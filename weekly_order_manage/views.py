from utils.success_failer import success_response, failure_response
from utils.pagination import CustomPagination
from .serializers import DeliverListSerializer
from .models import DeliveryDay
from .serializers import OrderListSerializer
from .serializers import OrderSerializer, DeliveryDaySerializer
from .models import Order, DeliveryDay
from rest_framework import generics, permissions
from auths.models import CommitmentForSixMonths
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import stripe
from django.conf import settings
from django.db import transaction

from .models import (
    OrderShippingAddress, StripeCustomer, Order,
    DeliveryWeek, DeliveryDay, DeliveryItem,
)
from .serializers import (
    OrderSerializer, DeliveryDaySerializer, DeliverListSerializer, OrderPauseSerializer
)

from products.models import Product

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY




class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).prefetch_related(
            'delivery_weeks__delivery_days__order_items__product'
        )

    @action(detail=True, methods=['post'])
    def create_setup_intent(self, request, pk=None):
        """Create a SetupIntent for saving payment method"""
        order = self.get_object()
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=order.user.stripe_customer.stripe_customer_id,
                payment_method_types=['card'],
                metadata={'order_id': order.id}
            )

            # Save setup intent ID to order
            order.stripe_setup_intent_id = setup_intent.id
            order.save()

            return Response({'client_secret': setup_intent.client_secret})

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SetupCardForSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]
    """
    Setup card for future recurring payments WITHOUT charging initially
    """

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            subscription_type = request.data.get('subscription_type', 'weekly')

            # Get or create Stripe customer
            stripe_customer, created = StripeCustomer.objects.get_or_create(
                user=user,
                defaults={'stripe_customer_id': ''}
            )

            # Create Stripe customer if doesn't exist
            if not stripe_customer.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f"{user.first_name} {user.last_name}",
                    metadata={'user_id': user.id}
                )
                stripe_customer.stripe_customer_id = customer.id
                stripe_customer.save()

            # Create SetupIntent to save card without charging
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer.stripe_customer_id,
                payment_method_types=['card'],
                usage='off_session',  # For future payments
                metadata={
                    'user_id': user.id,
                    'subscription_type': subscription_type
                }
            )

            return Response({
                'success': True,
                'statusCode': 200,
                'client_secret': setup_intent.client_secret,
                'setup_intent_id': setup_intent.id,
                'customer_id': stripe_customer.stripe_customer_id,
                'message': 'Card setup initialized. Complete card verification to start subscription.'
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmCardAndCreateSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        setup_intent_id = request.data.get('setup_intent_id')
        order_data = request.data.get('order_data')
        subscription_type = request.data.get('subscription_type', 'weekly')
        subscription_duration = request.data.get(
            'subscription_duration', '1_month')
        shipping_info = request.data.get('shipping_information', {})
        payment_method_id = None
        if not setup_intent_id:
            return Response({'error': 'Setup intent ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)
            payment_method_id = setup_intent.get(
                'payment_method')  # Fix: declare this explicitly
            print("payment id ", payment_method_id)

            if not payment_method_id and setup_intent['status'] == 'requires_payment_method':
                test_payment_method = stripe.PaymentMethod.create(
                    type='card',
                    card={'token': 'tok_visa'}
                )
                payment_method_id = test_payment_method.id

                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=setup_intent['customer']
                )

            if not payment_method_id:
                return Response({"error": "No payment method found."}, status=status.HTTP_400_BAD_REQUEST)

            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

            # Get or create local StripeCustomer object
            stripe_customer, created = StripeCustomer.objects.get_or_create(
                stripe_customer_id=setup_intent['customer'],
                defaults={'user': request.user}
            )

            # Save payment method details to DB
            stripe_customer.default_payment_method_id = payment_method_id
            stripe_customer.card_last_four = payment_method['card']['last4']
            stripe_customer.card_brand = payment_method['card']['brand']
            stripe_customer.card_exp_month = payment_method['card']['exp_month']
            stripe_customer.card_exp_year = payment_method['card']['exp_year']
            stripe_customer.is_card_valid = True
            stripe_customer.save()

            user = request.user
            total_amount = self.calculate_order_total(
                user, order_data)  # a single week total amount

            order_start_date = timezone.now() + timedelta(days=3)
            full_order_price = 0
            if subscription_duration == '6_month':
                end_date = order_start_date + timedelta(days=182)  # 26 weeks
                duration_number = 6
                full_order_price = total_amount * 26  # 26 weeks
            else:
                end_date = order_start_date + timedelta(days=28)  # 4 weeks
                duration_number = 1
                full_order_price = total_amount * 4

            today = timezone.now()
            days_until_monday = (7 - today.weekday()) % 7
            next_billing_date = today + timedelta(days=days_until_monday or 7)

            with transaction.atomic():
                shipping_address = OrderShippingAddress.objects.create(
                    user=user,
                    shipping_address=shipping_info.get('shipping_address'),
                    phone_number=shipping_info.get('phone_number'),
                    email=shipping_info.get('email'),
                    postal_code=shipping_info.get('postal_code'),
                    area_id=shipping_info.get('area')
                )

                order = Order.objects.create(
                    user=user,
                    shipping_address=shipping_address,
                    subscription_type=subscription_type,
                    subscription_duration=duration_number,
                    status='active',
                    start_date=order_start_date,
                    end_date=end_date,
                    next_billing_date=next_billing_date,
                    next_delivery_date=order_start_date,
                    stripe_customer_id=stripe_customer.stripe_customer_id,
                    stripe_payment_method_id=payment_method_id,
                    stripe_setup_intent_id=setup_intent_id,
                    weekly_amount=round(total_amount, 2),
                    total_amount=round(full_order_price, 2),
                    is_order_active=True
                )
                print("🪲 total a singel week amount :", total_amount)
                print("🐜 total this order amount :", full_order_price)

                self.create_delivery_schedule(
                    order, order_data, order_start_date, end_date)

                return Response({
                    'success': True,
                    'statusCode': 200,
                    'message': 'Subscription created successfully! First payment will be charged automatically.',
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'next_billing_date': order.next_billing_date,
                    'subscription_type': order.subscription_type,
                    'total_amount': str(total_amount),
                    'subscription_duration': order.subscription_duration,
                    'subscription_start_date': order.start_date,
                    'subscription_end_date': order.end_date,
                    'stripe_customer_id': stripe_customer.stripe_customer_id,
                    'card_info': {
                        'last_four': stripe_customer.card_last_four,
                        'brand': stripe_customer.card_brand,
                        'exp_month': stripe_customer.card_exp_month,
                        'exp_year': stripe_customer.card_exp_year
                    }
                }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calculate_order_total(self, user, order_data):
        """Calculate total amount from order data"""
        is_committed = CommitmentForSixMonths.objects.filter(
            user=user, commitment_status=True).exists()

        total = Decimal('0.00')
        print(
            f"▶️Calculating total for user {user.id} with commitment status {is_committed}")

        for day_order in order_data:
            number_of_people = int(day_order.get('number_of_people', 1))
            for item in day_order.get('order_items', []):
                product_id = item.get('product')
                quantity = int(item.get('quantity', 1))

                product = Product.objects.get(id=product_id)
                price = product.price

                if number_of_people > 1:
                    price *= number_of_people

                total += price * quantity
                print(
                    f"Added {quantity} of product {product_id} at price {price} for total {total}")

        # Apply 10% discount if committed
        if is_committed:
            discount_rate = Decimal('0.10')
            total *= (Decimal('1.00') - discount_rate)
            print(f"😐Total after commitment discount: {total}")

        # Add delivery charge of 1.79 EUR per delivery day
        delivery_charge = Decimal('1.79') * len(order_data)
        print(
            f"🚌Adding delivery charge of {delivery_charge} EUR for {len(order_data)} delivery days")
        total += delivery_charge
        print(f"✅Total after adding delivery charge: {total}")
        return total.quantize(Decimal('0.01'))

    def create_delivery_schedule(self, order, order_data, start_date, end_date):
        current_date = start_date
        week_number = 1
        weekdays = ['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday']

        if order.subscription_type == 'weekly':
            while (end_date - current_date).days >= 6:  
                delivery_week = DeliveryWeek.objects.create(
                    order=order,
                    week_number=week_number
                )

                for day_data in order_data:
                    day_name = day_data.get('delivery_day')
                    days_ahead = weekdays.index(
                        day_name) - current_date.weekday()
                    if days_ahead < 0:
                        days_ahead += 7
                    delivery_date = current_date + timedelta(days=days_ahead)

                    if delivery_date <= end_date:
                        delivery_day = DeliveryDay.objects.create(
                            week=delivery_week,
                            day_name=day_name,
                            delivery_date=delivery_date,
                            number_of_people=day_data.get(
                                'number_of_people', 1),
                            status='pending'
                        )

                        for item in day_data.get('order_items', []):

                            try:
                                product_id = item.get('product')
                                product = Product.objects.get(
                                    id=product_id)  # Ensure FK is valid

                                DeliveryItem.objects.create(
                                    delivery_day=delivery_day,
                                    product=product,
                                    quantity=item.get('quantity', 1)
                                )
                            except Product.DoesNotExist:
                                # Optionally skip or log error
                                print(
                                    f"Product with ID {product_id} does not exist. Skipping this item.")

                current_date += timedelta(days=7)
                week_number += 1


class DeliveryDayViewSet(viewsets.ModelViewSet):
    queryset = DeliveryDay.objects.all()
    serializer_class = DeliveryDaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(week__order__user=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a specific delivery day"""
        delivery_day = self.get_object()

        if delivery_day.delivery_date - date.today() < timedelta(days=3):
            return Response(
                {'error': 'Cancellation must be at least 3 days before delivery'},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery_day.is_cancelled = True
        delivery_day.status = 'cancelled'
        delivery_day.save()

        return Response({'status': 'delivery cancelled'})

    @action(detail=True, methods=['post'])
    def update_items(self, request, pk=None):
        """Update products for a delivery day"""
        delivery_day = self.get_object()
        items = request.data.get('items', [])

        # Clear existing items
        delivery_day.order_items.all().delete()

        # Add new items
        for item in items:
            DeliveryItem.objects.create(
                delivery_day=delivery_day,
                product_id=item['product_id'],
                quantity=item['quantity']
            )

        return Response({'status': 'delivery items updated'})


class OrderListAPIView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser or getattr(self.request.user, 'role', None) == 'admin': 
            return Order.objects.all().only(
                'id', 'order_number', 'status', 'start_date', 'end_date', 'total_amount'
            )
        return Order.objects.filter(user=user).only(
            'id', 'order_number', 'status', 'start_date', 'end_date', 'total_amount'
        )



class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
        # return Order.objects.filter()


class DeliveryDayListAPIView(generics.ListAPIView):
    serializer_class = DeliverListSerializer
    # permission_classes = [permissions.IsAdminUser]
    pagination_class = CustomPagination

    def get_queryset(self):
        qs = DeliveryDay.objects.select_related(
            'week',
            'week__order',
            'week__order__shipping_address'
        ).prefetch_related(
            'order_items__product'
        )

        filter_param = self.request.query_params.get('filter', None)
        order_number = self.request.query_params.get('order_number', None)
        user_email = self.request.query_params.get('user_email', None)
        delivery_date = self.request.query_params.get('delivery_date', None)
        area_name = self.request.query_params.get('area_name', None)
        postal_code = self.request.query_params.get('postal_code', None)

        if filter_param != 'all':
            qs = qs.filter(delivery_date__gte=date.today())

        if order_number:
            qs = qs.filter(week__order__order_number__icontains=order_number)

        if user_email:
            qs = qs.filter(week__order__user__email__icontains=user_email)

        if delivery_date:
            qs = qs.filter(delivery_date=delivery_date)

        # New filters for area and postal code
        if area_name:
            qs = qs.filter(
                week__order__shipping_address__area_name__icontains=area_name)

        if postal_code:
            qs = qs.filter(
                week__order__shipping_address__postal_code__icontains=postal_code)

        qs = qs.order_by('delivery_date')

        return qs


class AllDeliveryDayAPIView(generics.ListAPIView):
    serializer_class = DeliverListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination        # 🔑 enable paging

    def get_queryset(self):
        qs = DeliveryDay.objects.filter(is_cancelled=False)
        today = date.today()
        filter_by = self.request.query_params.get(
            'filter')  # this_week | this_month | all
        sort = self.request.query_params.get('sort')    # new | old

        # --- date-range filters ----------------------------
        if filter_by == 'this_week':
            start = today - timedelta(days=today.weekday())     # Monday
            end = start + timedelta(days=6)                   # Sunday
            qs = qs.filter(delivery_date__range=(start, end))

        elif filter_by == 'this_month':
            start = today.replace(day=1)
            next_month = (today.replace(day=28) +
                          timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
            qs = qs.filter(delivery_date__range=(start, end))

        elif filter_by != 'all':
            # default → next 3 days
            qs = qs.filter(delivery_date__range=(
                today, today + timedelta(days=3)))

        # --- sorting --------------------------------------
        if sort == 'old':
            # oldest first, grouped by week
            qs = qs.order_by('week__id', 'delivery_date')
        else:
            # newest first (default)
            qs = qs.order_by('week__id', '-delivery_date')

        return qs.select_related(
            'week',
            'week__order',
            'week__order__shipping_address'
        ).prefetch_related(
            'order_items__product'
        )


class SingleDeliveryDayAPIView(generics.RetrieveAPIView):
    serializer_class = DeliverListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeliveryDay.objects.all()


class CancelDeliveryDayAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = DeliverListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeliveryDay.objects.filter()

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        delivery_day = self.get_object()

        if delivery_day.is_cancelled:
            return failure_response("Already cancelled.", status.HTTP_400_BAD_REQUEST)

        # 1️⃣ cancel the day
        delivery_day.is_cancelled = True
        delivery_day.status = 'cancelled'
        delivery_day.save()

        return success_response("Delivery day & order cancelled.", status.HTTP_200_OK)
class OrderPauseAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderPauseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.all()
    
    def post(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        order.is_order_pause = True
        order.save()
        return success_response("Order paused.", {"is_order_pause": order.is_order_pause},status.HTTP_200_OK)
    
    def delete(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        order.is_order_pause = False
        order.save()
        return success_response("Order resumed.",{"is_order_pause": order.is_order_pause}, status.HTTP_200_OK )
    
    