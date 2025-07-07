
from django.db.models import Case, When, IntegerField
from utils.IsAdminOrStaff import IsAdminOrStaff
from .serializers import DeliveryActionRequestSerializer, SubscriptionStatusSerializer
from .models import Order, DeliveryActionRequest
from datetime import date, timedelta
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import DeliveryScheduleSerializer
from .models import DeliverySchedule
from rest_framework import viewsets, filters
import logging
from auths.models import CommitmentForSixMonths
from .serializers import (
    OrderCreateSerializer, OrderDetailSerializer,
    OrderStatusUpdateSerializer, OrderAcceptanceSerializer,
    PauseRequestSerializer, OrderDataSerializer, OrderDataForAdminSerializer
)
from .models import Order, OrderData, OrderItem, Payment, PauseRequest
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import viewsets, status, permissions
from django.contrib.auth import get_user_model
from rest_framework import status
from .models import Order, Payment
from django.db.models import Sum, F, Case, When, IntegerField
from datetime import datetime
from .models import OrderItem
from django.db.models.functions import TruncMonth
import io
from datetime import timedelta
from django.core.mail import EmailMessage
from rest_framework.decorators import api_view
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from django.core.exceptions import ValidationError
from .models import OrderData
from .serializers import OrderDataForAdminSerializer
import openpyxl
from .models import Area
from .serializers import AreaRevenueSerializer
from utils.IsAdminuser import IsDeliveryManOrAdminOrStaff
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_date
from rest_framework import status, permissions
from .models import Order, OrderData, OrderItem, Payment, StripeCustomer
from .serializers import OrderCreateSerializer
from .stripe_helpers import get_or_create_stripe_customer
from products.models import Product
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from subscriptions.serializers import FreeBoxRequestSerializer, FreeBoxRequest
import json
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta, date
from datetime import date, datetime, timedelta
from django.views import View
from .models import DeliverySchedule, DeliveryProduct, Product
import calendar
from decimal import Decimal
from django.db import transaction
from utils.pagination import CustomPagination
from requests.auth import HTTPBasicAuth
import requests
from autoemail.tasks import send_order_creation_email, send_payment_confirmation_email
from utils.success_failer import success_response, failure_response
import paypalrestsdk
import stripe
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.utils.timezone import now
now()


logger = logging.getLogger(__name__)


class OrderCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(
            data=request.data, context={'request': request})

        if serializer.is_valid():
            order = serializer.save()
            
            return success_response(
                message="Order created successfully",
                data=OrderDetailSerializer(order).data,
                status=status.HTTP_201_CREATED
            )
        else:
            
            return failure_response(
                message="Order creation failed",
                error=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderStatusUpdateSerializer
        elif self.action == 'accept_order':
            return OrderAcceptanceSerializer
        return OrderDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        return success_response(
            message="Order created successfully",
            data=OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        if request.user.is_staff:
            queryset = self.queryset
        else:
            queryset = self.queryset.filter(user=request.user)
        queryset = queryset.order_by(
            Case(
                
                When(status='paid', then=1),
                default=0,
                output_field=IntegerField()
            ),
            '-order_created_date'  
        )

        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = OrderDetailSerializer(result_page, many=True)

        
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve a single order by its ID"""
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def accept_order(self, request, pk=None):
        order = self.get_object()
        serializer = OrderAcceptanceSerializer(
            order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OrderAcceptanceView(APIView):
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return failure_response("Order not found", status=status.HTTP_404_NOT_FOUND)

        serializer = OrderAcceptanceSerializer(
            order, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return success_response("Order status updated successfully.", serializer.data, status.HTTP_200_OK)
        return failure_response("Failed to update order status", serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:

            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrderStatusUpdateSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrderStatusUpdateSerializer(
            order, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Order updated successfully",
                    "success": True, "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"detail": "Failed to update order", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class PauseOrderRequestView(APIView):

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            user = request.user
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if order.status == 'paused':
            return Response(
                {"detail": "This order is already paused"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user != order.user and not request.user.is_staff:
            return Response(
                {"detail": "You don't have permission to pause this order."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PauseRequestSerializer(data=request.data)
        if serializer.is_valid():
            pause_request = serializer.save(order=order, user=request.user)

            return Response(
                {"detail": "Pause request submitted successfully. Awaiting approval."},
                status=status.HTTP_202_ACCEPTED
            )
        return Response(
            {"detail": "Failed to submit pause request",
                "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class ResumeOrderView(APIView):
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if order.status != 'paused':
            return Response(
                {"detail": "Order is not paused"},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'processing'
        order.save()

        return Response(
            {"detail": "Order resumed successfully."},
            status=status.HTTP_200_OK
        )


class DeleteOrderDataView(APIView):
    def delete(self, request, order_data_id):
        try:
            order_data = OrderData.objects.get(id=order_data_id)
        except OrderData.DoesNotExist:
            return failure_response(
                "Order data not found.",
                {},
                status.HTTP_404_NOT_FOUND
            )

        order = order_data.order

        order_items = OrderItem.objects.filter(order_data=order_data)
        if order_items:
            order_items.delete()
        order_data.delete()
        self.update_order_total_amount(order)

        return success_response(
            "Order data and associated items have been deleted.",
            {},
            status.HTTP_200_OK
        )

    def update_order_total_amount(self, order):
        """
        Recalculate the total amount of an order after deleting its order items.
        """
        total_amount = 0
        for order_data in order.order_data.all():
            for order_item in order_data.order_items.all():
                total_amount += order_item.price * order_item.quantity

        order.total_amount = total_amount
        order.save()


class UpdateOrderDataStatusView(APIView):
    def patch(self, request, order_data_id):
        try:
            order_data = OrderData.objects.get(id=order_data_id)
        except OrderData.DoesNotExist:
            return Response({"detail": "Order data not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderDataSerializer(
            order_data, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "detail": "Order data status updated successfully.",
                "order_data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroupOrdersByDeliveryDate(APIView):
    permission_classes = [IsDeliveryManOrAdminOrStaff]

    def get(self, request):
        today = date.today()
        day_index_today = today.weekday()
        day_name_list = list(calendar.day_name)

        grouped_orders = defaultdict(list)

        
        order_data_list = OrderData.objects.select_related('order') \
            .prefetch_related('order_items') \
            .filter(order__is_subscription_active=True)

        for order_data in order_data_list:
            serialized_order_data = OrderDataSerializer(order_data).data

            day_name = serialized_order_data['delivery_day']
            if day_name not in calendar.day_name:
                continue  

            
            target_index = day_name_list.index(day_name)
            days_ahead = (target_index - day_index_today + 7) % 7 or 7
            next_delivery_date = today + timedelta(days=days_ahead)

            serialized_order_data['converted_delivery_date'] = next_delivery_date.isoformat(
            )

            grouped_orders[day_name].append(serialized_order_data)

        return Response(grouped_orders)



User = get_user_model()
stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


class CreatePaymentIntentView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            order_id = request.data.get('order_id')

            if not order_id:
                return Response({"error": "Order ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.get(id=order_id)
            if order.payment_status:
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Payment has already been completed.',
                    'order_id': order.id
                }, status=status.HTTP_200_OK)

            if order.status in ['paused', 'cancelled']:
                return Response({"error": "Order is paused or cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            total_amount = Decimal(0.0)

            for order_data in order.order_data.all():

                if not order_data.is_cancelled:
                    for item in order_data.order_items.all():
                        item_total_price = Decimal(
                            item.price) * Decimal(item.quantity)
                        total_amount += item_total_price
            print("Total Amount:", total_amount)
            if total_amount <= 0:
                return Response({"error": "Invalid total amount."}, status=status.HTTP_400_BAD_REQUEST)

            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),
                currency='eur',
            )

            return Response({
                'success': True,
                "statusCode": 200,
                'client_secret': payment_intent.client_secret,
                "payment_id": payment_intent.id,
                'total_amount': total_amount,
                'message': 'Payment intent created successfully. Please complete the payment.'
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentConfirmAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            payment_intent_id = request.data.get('payment_id')
            order_id = request.data.get('order_id')

            if not payment_intent_id or not order_id:
                return Response({"error": "Payment intent ID and order ID are required."}, status=status.HTTP_400_BAD_REQUEST)
            order = Order.objects.get(id=order_id)
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if order.payment_status:
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Payment has already been completed.',
                    'order_id': order.id
                }, status=status.HTTP_200_OK)

            if payment_intent['status'] == 'succeeded':
                order.status = 'paid'
                order.payment_status = True
                order.save()

                payment_type = order.subscription_type if order.subscription_type in [
                    'weekly', 'monthly'] else 'unknown'

                payment = Payment.objects.create(
                    user=order.user,
                    subscription=order,
                    amount=Decimal(payment_intent['amount_received']) / 100,
                    is_paid=True,
                    transaction_id=payment_intent_id,
                    payment_type=payment_type,
                    payment_date=timezone.now(),
                )

                payment.orders.add(order)
                payment.save()
                send_payment_confirmation_email.delay(
                    to_email=order.user.email,
                    customer_name=order.user.username,
                    
                    amount=Decimal(payment_intent['amount_received']) / 100,
                    transaction_id=payment_intent_id
                )

                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Payment confirmed successfully.',
                    'payment_id': payment.id
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": f"Payment not succeeded. Current status: {payment_intent['status']}."
                }, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)


paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

client_id = settings.PAYPAL_CLIENT_ID
client_secret = settings.PAYPAL_CLIENT_SECRET


def get_access_token():
    url = "https://api.sandbox.paypal.com/v1/oauth2/token"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials'
    }
    auth = HTTPBasicAuth(client_id, client_secret)
    response = requests.post(url, headers=headers, data=data, auth=auth)

    if response.status_code == 200:
        access_token = response.json()['access_token']

        print(f"Access Token: {access_token}")
        return access_token
    else:

        print(f"Failed to retrieve access token from PayPal: {response.text}")
        return None


def get_payment_details(payment_id, access_token):
    url = f"https://api.sandbox.paypal.com/v2/checkout/orders/{payment_id}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)

    print(f"PayPal API Response: {response.status_code} - {response.text}")

    if response.status_code == 200:
        return response.json()
    else:

        print(
            f"Failed to retrieve payment details from PayPal: {response.text}")
        return None


class CreatePaymentByPayPalIntentView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            order_id = request.data.get('order_id')

            if not order_id:
                return Response({"error": "Order ID is required."}, status=status.HTTP_400_BAD_REQUEST)
            order = Order.objects.get(id=order_id)
            if order.payment_status:
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Payment has already been completed.',
                    'order_id': order.id
                }, status=status.HTTP_200_OK)

            if order.status in ['paused', 'cancelled']:
                return Response({"error": "Order is paused or cancelled."}, status=status.HTTP_400_BAD_REQUEST)

            total_amount = Decimal(0.0)

            for order_data in order.order_data.all():
                if not order_data.is_cancelled:
                    for item in order_data.order_items.all():
                        item_total_price = Decimal(
                            item.price) * Decimal(item.quantity)
                        total_amount += item_total_price

            print("Total Amount:", total_amount)
            if total_amount <= 0:
                return Response({"error": "Invalid total amount."}, status=status.HTTP_400_BAD_REQUEST)

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": str(total_amount),
                        "currency": "EUR"
                    },
                    "description": f"Payment for order {order.id}"
                }],
                "redirect_urls": {
                    "return_url": "https://gepixelitfrontend.vercel.app/payment/paymentSuccess",
                    "cancel_url": "https://gepixelitfrontend.vercel.app/payment/paymentFail"
                }
            })

            if payment.create():
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'payment_id': payment.id,
                    'total_amount': total_amount,
                    'message': 'Payment created successfully. Please complete the payment on PayPal.'
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Failed to create payment."}, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except paypalrestsdk.exceptions.PayPalHttpError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentConfirmByPayPalAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            payment_id = request.data.get('payment_id')
            order_id = request.data.get('order_id')

            if not payment_id or not order_id:
                print("Payment ID or Order ID is missing.")
                return Response({"error": "Payment ID and order ID are required."}, status=status.HTTP_400_BAD_REQUEST)

            print(f"Received Payment ID: {payment_id}")

            order = Order.objects.get(id=order_id)
            access_token = get_access_token()
            if not access_token:
                return JsonResponse({"error": "Unable to retrieve access token from PayPal"}, status=status.HTTP_400_BAD_REQUEST)

            payment_details = get_payment_details(payment_id, access_token)

            if order.payment_status:
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Payment has already been completed.',
                    'order_id': order.id
                }, status=status.HTTP_200_OK)

            if payment_details is None:
                print("Payment details could not be retrieved.")
                return Response({"error": "Failed to retrieve payment details from PayPal."}, status=status.HTTP_400_BAD_REQUEST)

            if payment_details.get('status') == "COMPLETED":
                order.status = 'paid'
                order.payment_status = True
                order.save()

                payment_type = order.subscription_type if order.subscription_type in [
                    'weekly', 'monthly'] else 'unknown'

                payment_record = Payment.objects.create(
                    user=order.user,
                    subscription=order,
                    amount=Decimal(
                        payment_details['purchase_units'][0]['amount']['value']),
                    is_paid=True,
                    transaction_id=payment_id,
                    payment_type=payment_type,
                    payment_date=timezone.now(),
                )

                payment_record.orders.add(order)
                payment_record.save()
                
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Payment confirmed successfully.',
                    'payment_id': payment_record.id
                }, status=status.HTTP_200_OK)
            else:
                print(
                    f"Payment status is not completed. Current status: {payment_details.get('status')}")
                return Response({
                    "error": f"Payment not succeeded. Current status: {payment_details.get('status')}"
                }, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            print(f"Request Error: {str(e)}")
            return Response({"error": f"Request Error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            print("Order not found.")
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)


class DashboardOverview(APIView):

    def get(self, request, *args, **kwargs):
        
        current_year = datetime.now().year

        
        monthly_revenue = OrderItem.objects.filter(
            order__payment_status=True,  
            order__order_created_date__year=current_year
        ).annotate(month=TruncMonth('order__order_created_date')).values('month').annotate(
            revenue=Sum(F('price') * F('quantity'))
        ).order_by('month')

        
        month_names = [
            "January", "February", "March", "April", "May", "June", "July", "August",
            "September", "October", "November", "December"
        ]

        
        monthly_revenue_data = {month: 0 for month in month_names}

        
        for data in monthly_revenue:
            month_number = data['month'].month
            
            month_name = month_names[month_number - 1]
            monthly_revenue_data[month_name] = float(data['revenue'] or 0)

        
        total_orders = Order.objects.count()

        
        total_delivered_orders = Order.objects.filter(
            status='delivered').count()

        
        total_cancelled_orders = Order.objects.filter(
            status='cancelled').count()

        
        total_weekly_revenue = Payment.objects.filter(payment_type='weekly', is_paid=True).aggregate(
            revenue=Sum('amount')
        )['revenue'] or 0

        total_monthly_revenue = Payment.objects.filter(payment_type='monthly', is_paid=True).aggregate(
            revenue=Sum('amount')
        )['revenue'] or 0

        
        pending_pause_requests = PauseRequest.objects.filter(
            status='pending').count()
        approved_pause_requests = PauseRequest.objects.filter(
            status='approved').count()
        rejected_pause_requests = PauseRequest.objects.filter(
            status='rejected').count()

        
        response_data = {
            "monthly_revenue": monthly_revenue_data,  
            "total_orders": total_orders,
            "total_delivered_orders": total_delivered_orders,
            "total_cancelled_orders": total_cancelled_orders,
            "total_weekly_revenue": total_weekly_revenue,
            "total_monthly_revenue": total_monthly_revenue,
            "pending_pause_requests": pending_pause_requests,
            "approved_pause_requests": approved_pause_requests,
            "rejected_pause_requests": rejected_pause_requests
        }

        return Response({
            'success': True,
            "statusCode": 200,
            'message': 'Dashboard data fetched successfully.',
            'Data': response_data
        }, status=status.HTTP_200_OK)





def generate_pdf(order_data, message=""):
    buffer = io.BytesIO()

    
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    
    header = ['Delivery Date', 'Order ID', 'User',
              'Shipping Address', 'Phone Number', 'Product Name', 'Quantity']

    
    if not order_data:
        table_data = [[message]]
    else:
        
        table_data = []
        for order in order_data:
            user_info = f"{order['user_details']['first_name']} {order['user_details']['last_name']} ({order['user_details']['email']})"

            
            for item in order['items']:
                table_data.append([
                    order['delivery_date'],
                    order['id'],
                    user_info,
                    order['shipping_address'],
                    order['phone_number'],
                    item['product_details']['name'],
                    item['quantity']
                ])

        
        table_data.append([])

    
    table = Table([header] + table_data,
                  colWidths=[100, 80, 160, 160, 120, 180, 80])

    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),  
        ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),  
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  
        ('GRID', (0, 0), (-1, -1), 0.5, (0, 0, 0)),  
        ('FONTSIZE', (0, 0), (-1, -1), 8),  
        ('TOPPADDING', (0, 0), (-1, -1), 6),  
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  
    ])

    table.setStyle(style)

    
    elements.append(table)

    
    doc.build(elements)

    buffer.seek(0)
    return buffer


def generate_excel(order_data, message=""):
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Order Details"

    
    header = ['area', 'postal_code', 'Delivery Date', 'Order ID', 'User',
              'Shipping Address', 'Phone Number', 'Product Name', 'Quantity']
    ws.append(header)

    
    if not order_data:
        ws.append([message])
    else:
        
        for order in order_data:
            user_info = f"{order['user_details']['first_name']} {order['user_details']['last_name']} ({order['user_details']['email']})"
            for item in order['items']:
                ws.append([
                    order['area'],
                    order['postal_code'],
                    order['delivery_date'],
                    order['id'],
                    user_info,
                    order['shipping_address'],
                    order['phone_number'],
                    item['product_details']['name'],
                    item['quantity']
                ])

    
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer


USER_MODEL = get_user_model()


def send_email_with_files(pdf_buffer, excel_buffer, email):
    try:
        
        subject = "Order Details Report".encode(
            'utf-8', 'ignore').decode('utf-8', 'ignore')
        body = "Please find attached the order details in PDF and Excel format.".encode(
            'utf-8', 'ignore').decode('utf-8', 'ignore')

        
        email_message = EmailMessage(
            subject,
            body,
            
            settings.DEFAULT_FROM_EMAIL,
            [email],  
        )

        
        email_message.attach("order_details_report.pdf",
                             pdf_buffer.read(), "application/pdf")
        email_message.attach("order_details_report.xlsx", excel_buffer.read(
        ), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        
        email_message.send()
    except Exception as e:
        print(f"Error sending email: {e}")
        raise ValidationError(f"Error sending email: {e}")


@api_view(['POST'])
def send_order_report(request):
    
    filter_type = request.data.get(
        "filter_type", "today")  
    email = request.data.get("email")

    if not email:
        raise ValidationError("Email is required.")

    
    email = email.strip().encode('utf-8', 'ignore').decode('utf-8', 'ignore')

    
    if filter_type == "today":
        start_date = timezone.now().date()
        end_date = start_date
    elif filter_type == "next_3_days":
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=3)
    elif filter_type == "weekly":
        start_date = timezone.now().date()
        end_date = start_date + timedelta(weeks=1)
    else:
        raise ValidationError("Invalid filter type.")

    orders = OrderData.objects.filter(
        delivery_date__range=[start_date, end_date])

    serializer = OrderDataForAdminSerializer(orders, many=True)

    if not orders:
        message = "No orders found for the selected date range."
    else:
        message = ""

    pdf_buffer = generate_pdf(serializer.data, message)

    excel_buffer = generate_excel(serializer.data, message)
    
    send_email_with_files(pdf_buffer, excel_buffer, email)

    return JsonResponse({"message": "Order report sent successfully.", 'success': True})


class CreateStripPaymentIntentView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            total_amount = request.data.get('total_amount')
            if not total_amount:
                return Response({"error": "Total amount is required."}, status=status.HTTP_400_BAD_REQUEST)

            if total_amount <= 0:
                return Response({"error": "Invalid total amount."}, status=status.HTTP_400_BAD_REQUEST)
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),  
                currency='eur',
            )

            return Response({
                'success': True,
                "statusCode": 200,
                'client_secret': payment_intent.client_secret,
                "payment_id": payment_intent.id,
                'total_amount': total_amount,
                'message': 'Payment intent created successfully. Please complete the payment.'
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentStripeConfirmAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            print("Request data:", request.data)

            payment_intent_id = request.data.get('payment_id')
            order_data = request.data.get('order_data')
            subscription_type = request.data.get('subscription_type')

            if not payment_intent_id:
                return Response({"error": "Zahlungs-ID ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)

            if not order_data:
                return Response({"error": "Bestelldaten sind erforderlich."}, status=status.HTTP_400_BAD_REQUEST)

            if not subscription_type:
                return Response({"error": "Abonnementtyp ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)

            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if payment_intent['status'] != 'succeeded':
                return Response({
                    "error": f"Zahlung nicht erfolgreich. Aktueller Status: {payment_intent['status']}."
                }, status=status.HTTP_400_BAD_REQUEST)

            order_data_serializer = OrderCreateSerializer(data={
                'subscription_type': subscription_type,
                'order_data': order_data,
                'shipping_address': request.data.get('shipping_address'),
                'phone_number': request.data.get('phone_number'),
                'postal_code': request.data.get('postal_code'),
                'area': request.data.get('area'),
                'email': request.data.get('email'),
            }, context={'request': request})

            if order_data_serializer.is_valid():
                order = order_data_serializer.save(
                    payment_status=True, payment_date=timezone.now())

                payment = Payment.objects.create(
                    user=order.user,
                    subscription=order,
                    amount=Decimal(payment_intent['amount_received']) / 100,
                    is_paid=True,
                    transaction_id=payment_intent_id,
                    payment_type=subscription_type,
                    payment_date=timezone.now(),
                )

                payment.orders.add(order)
                payment.save()

                order.status = 'pending'
                order.payment_status = True
                order.save()

                try:
                    subject = "Zahlungsbestätigung – Ihre Bestellung"
                    message = f"Sehr geehrte/r {order.user.first_name},\n\n" \
                        f"Ihre Zahlung für die Bestellung #{order.order_number} wurde erfolgreich verarbeitet.\n\n" \
                        f"Bestelldetails:\n" \
                        f"Lieferadresse: {order.shipping_address}\n" \
                        f"Telefonnummer: {order.phone_number}\n\n" \
                        f"Vielen Dank für Ihren Einkauf!\n\n" \
                        f"Mit freundlichen Grüßen,\n" \
                        f"Ihr Unternehmen"

                    from_email = settings.DEFAULT_FROM_EMAIL
                    to_email = request.data.get('email')

                    email = EmailMessage(
                        subject, message, from_email, [to_email])
                    email.send()
                    print("E-Mail erfolgreich gesendet")

                except Exception as e:
                    print(f"Fehler beim Senden der E-Mail: {str(e)}")

                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Zahlung bestätigt und Bestellung erfolgreich erstellt.',
                    'payment_id': payment.id,
                    'order_id': order.id
                }, status=status.HTTP_200_OK)

            else:
                return Response({
                    "error": "Ungültige Bestelldaten.",
                    "details": order_data_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe-Fehler: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("Fehler:", str(e))
            return Response({"error": f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreatePaymentPayPalIntentView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            total_amount = request.data.get('total_amount')

            if not total_amount:
                return Response({"error": "Total amount is required."}, status=status.HTTP_400_BAD_REQUEST)

            if float(total_amount) <= 0:
                return Response({"error": "Invalid total amount."}, status=status.HTTP_400_BAD_REQUEST)

            
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": str(total_amount),
                        "currency": "EUR"
                    },
                    "description": f"Payment for order with total amount of {total_amount} EUR"
                }],
                "redirect_urls": {
                    "return_url": "https://preisslersfruehstueck.at/payment/paymentSuccess",
                    "cancel_url": "https://preisslersfruehstueck.at/payment/paymentFail"
                }
            })

            
            if payment.create():
                approval_url = next(
                    link.href for link in payment.links if link.rel == "approval_url")
                return Response({
                    'success': True,
                    "statusCode": 200,
                    'payment_id': payment.id,
                    'total_amount': total_amount,
                    'approval_url': approval_url,
                    'message': 'Payment created successfully. Please complete the payment on PayPal.'
                }, status=status.HTTP_200_OK)
            else:
                logger.error(
                    f"PayPal payment creation failed: {payment.error}")
                return Response({"error": "Failed to create payment."}, status=status.HTTP_400_BAD_REQUEST)

        except paypalrestsdk.ResourceNotFound as e:
            return Response({"error": f"Resource not found: {str(e)}"}, status=status.HTTP_404_NOT_FOUND)
        except paypalrestsdk.ServerError as e:
            return Response({"error": f"PayPal server error: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except paypalrestsdk.ConnectionError as e:
            return Response({"error": f"Connection error: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({"error": f"Unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class PaymentConfirmByPayPalAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            payment_id = request.data.get('payment_id')
            order_data = request.data.get('order_data')
            subscription_type = request.data.get('subscription_type')

            
            if not payment_id or not order_data or not subscription_type:
                return Response(
                    {"error": "Zahlungs-ID, Bestelldaten und Abonnementtyp sind erforderlich."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            
            access_token = get_access_token()
            if not access_token:
                return Response(
                    {"error": "Zugriffstoken von PayPal konnte nicht abgerufen werden."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            
            payment_details = get_payment_details(payment_id, access_token)
            if not payment_details:
                return Response(
                    {"error": "Zahlungsdetails von PayPal konnten nicht abgerufen werden."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            
            if payment_details['status'] != 'COMPLETED':
                return Response(
                    {"error": "Die Zahlung wurde nicht abgeschlossen."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            
            order_data_serializer = OrderCreateSerializer(data={
                'subscription_type': subscription_type,
                'order_data': order_data,
                'shipping_address': request.data.get('shipping_address'),
                'phone_number': request.data.get('phone_number'),
                'postal_code': request.data.get('postal_code'),
                'area': request.data.get('area'),
                'email': request.data.get('email'),
            }, context={'request': request})

            if order_data_serializer.is_valid():
                order = order_data_serializer.save(
                    payment_status=True, payment_date=timezone.now())

                
                payment = Payment.objects.create(
                    user=order.user,
                    subscription=order,
                    amount=Decimal(
                        payment_details['purchase_units'][0]['amount']['value']),
                    is_paid=True,
                    transaction_id=payment_id,
                    payment_type=subscription_type,
                    payment_date=timezone.now(),
                )

                payment.orders.add(order)
                payment.save()

                
                order.status = 'pending'
                order.payment_status = True
                order.save()

                
                self.send_payment_confirmation_email(order)

                return Response({
                    'success': True,
                    "statusCode": 200,
                    'message': 'Zahlung bestätigt und Bestellung erfolgreich erstellt.',
                    'payment_id': payment.id,
                    'order_id': order.id
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid order data.", "details": order_data_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({"error": f"Request Error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error: {str(e)}")
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_payment_confirmation_email(self, order):
        """
        Sends a payment confirmation email to the user after successful payment and order creation.
        """
        try:
            subject = "Zahlungsbestätigung – Ihre Bestellung"
            message = f"Sehr geehrte/r {order.user.first_name},\n\n" \
                f"Ihre Zahlung für die Bestellung #{order.order_number} wurde erfolgreich verarbeitet.\n\n" \
                f"Bestelldetails:\n" \
                f"Lieferadresse: {order.shipping_address}\n" \
                f"Telefonnummer: {order.phone_number}\n\n" \
                f"Vielen Dank für Ihren Einkauf!\n\n" \
                f"Mit freundlichen Grüßen,\n" \
                f"Ihr Unternehmen"

            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = order.user.email

            email = EmailMessage(subject, message, from_email, [to_email])
            email.send()

        except Exception as e:
            print(f"Fehler beim Senden der E-Mail: {str(e)}")


class IsAdminOrDeliveryMan(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or
            request.user.is_superuser or
            getattr(request.user, 'role', None) == 'admin',
            getattr(request.user, 'role', None) == 'delivery_man'
        )


class AreaRevenueView(APIView):
    """
    API to get the total revenue for each area based on the orders and items.
    """
    permission_classes = [IsAdminOrDeliveryMan]

    def get(self, request, *args, **kwargs):
        area_revenue = Area.objects.annotate(
            total_revenue=Sum('order__items__revenue')
        ).values('id', 'name', 'total_revenue')
        serializer = AreaRevenueSerializer(area_revenue, many=True)
        return success_response(message="Area revenue fetched successfully", data=serializer.data, status=status.HTTP_200_OK)


class CombinedDeliveryListView(APIView):
    def get(self, request):
        
        date_filter = request.query_params.get('date', None)

        
        orders_query = OrderData.objects.filter(is_cancelled=False)
        if date_filter:
            orders_query = orders_query.filter(
                delivery_date=parse_date(date_filter))

        
        regular_orders = []
        for order_data in orders_query:
            order_items = order_data.order_items.all()
            items_data = []

            for item in order_items:
                product = item.product
                items_data.append({
                    "id": item.id,
                    "product": product.id,
                    "product_details": {
                        "image": product.image if product.image else None,
                        "name": product.name,
                        "price": float(product.price),
                        "revenue": float(product.revenue) if product.revenue else 0.0
                    },
                    "quantity": item.quantity,
                    "price": str(item.price),
                    "revenue": str(item.revenue) if item.revenue else "0.00"
                })

            user = order_data.order.user if order_data.order else None
            user_details = None
            if user:
                user_details = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }

            regular_orders.append({
                "id": order_data.id,
                "type": "regular_order",
                "delivery_date": order_data.delivery_date,
                "delivery_day": order_data.delivery_day,
                "user_details": user_details,
                "number_of_people": order_data.number_of_people,
                "is_delivered": order_data.is_delivered,
                "is_cancelled": order_data.is_cancelled,
                "order_status": order_data.order_status,
                "items": items_data,
                "shipping_address": order_data.order.shipping_address if order_data.order else None,
                "postal_code": order_data.order.postal_code if order_data.order else None,
                "phone_number": order_data.order.phone_number if order_data.order else None,
                "email": order_data.order.email if order_data.order else None,
                "area": order_data.order.area.name if order_data.order and order_data.order.area else None
            })

        
        free_box_query = FreeBoxRequest.objects.all()
        if date_filter:
            free_box_query = free_box_query.filter(
                date_of_delivery=parse_date(date_filter))

        
        free_boxes = []
        for box_request in free_box_query:
            products = []
            for product in box_request.box.items.all():
                products.append({
                    "id": product.id,
                    "name": product.name
                })

            free_boxes.append({
                "id": box_request.id,
                "type": "free_box",
                "delivery_date": box_request.date_of_delivery,
                "delivery_day": box_request.date_of_delivery.strftime("%A"),
                "number_of_people": box_request.number_of_people,
                "name": box_request.name,
                "phone_number": box_request.phone_number,
                "postal_code": box_request.postal_code,
                "address": box_request.address,
                "area_name": box_request.area_name.name if box_request.area_name else None,
                "email": box_request.email,
                "message": box_request.message,
                "delivery_status": box_request.delivery_status,
                "box_info": {
                    "id": box_request.box.id,
                    "name": box_request.box.name,
                    "products": products
                },
                "create_at": box_request.create_at
            })

        
        all_deliveries = regular_orders + free_boxes
        sorted_deliveries = sorted(
            all_deliveries,
            key=lambda x: x['delivery_date']
        )

        return Response({"success": True, "data": sorted_deliveries}, status=status.HTTP_200_OK)





stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

def get_or_create_stripe_customer(user, email=None):
    """
    Retrieves an existing Stripe customer ID for the user or creates a new one.
    IMPORTANT: This is a simplified placeholder. Implement robustly.
    """
    logger.info(
        f"Attempting to get/create Stripe customer for user_id: {user.id}, email: {email}")
    email_to_use_for_stripe = email
    if not email_to_use_for_stripe and hasattr(user, 'email') and user.email:
        email_to_use_for_stripe = user.email

    if not email_to_use_for_stripe:
        logger.error(
            f"Cannot create Stripe customer for user_id: {user.id}. Email is missing.")
        raise ValueError("An email is required to create a Stripe customer.")
    try:
        logger.info(
            f"Creating new Stripe customer for user_id: {user.id} with email: {email_to_use_for_stripe}")
        stripe_customer_obj = stripe.Customer.create(
            email=email_to_use_for_stripe,
            
            name=str(user),
            metadata={'django_user_id': user.id}
        )
        logger.info(
            f"Successfully created/retrieved Stripe customer: {stripe_customer_obj.id} for user_id: {user.id}")
        return stripe_customer_obj.id

    except stripe.error.StripeError as e:
        logger.error(
            f"Stripe API error in get_or_create_stripe_customer for user_id {user.id}: {e}", exc_info=True)
        raise  
    except Exception as e:
        logger.error(
            f"Unexpected error in get_or_create_stripe_customer for user_id {user.id}: {e}", exc_info=True)
        raise  


class CreateWeeklySubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info(
            f"CreateWeeklySubscriptionView POST request received from user: {request.user.id}")
        payload = request.data
        order_data_list = payload.get("order_data")

        if not order_data_list:
            logger.warning("Validation Error: 'order_data' is required.")
            return Response({"error": "order_data is required"}, status=status.HTTP_400_BAD_REQUEST)

        qty_map = defaultdict(int)
        product_ids_from_payload = set()
        for od_index, od_payload_item in enumerate(order_data_list):
            order_items_payload = od_payload_item.get("order_items", [])
            if not order_items_payload:  
                logger.warning(
                    f"Validation Error: order_data at index {od_index} has no order_items.")
                return Response({"error": f"Order data at index {od_index} must contain 'order_items'."}, status=status.HTTP_400_BAD_REQUEST)
            for item_payload in order_items_payload:
                product_id = item_payload.get("product")
                quantity = item_payload.get("quantity", 1)
                if not product_id:
                    logger.warning(
                        "Validation Error: Product ID missing in order_items.")
                    return Response({"error": "Product ID missing in one of the order_items."}, status=status.HTTP_400_BAD_REQUEST)
                if not isinstance(quantity, int) or quantity < 1:
                    logger.warning(
                        f"Validation Error: Invalid quantity '{quantity}' for product_id '{product_id}'.")
                    return Response({"error": f"Invalid quantity for product {product_id}. Must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

                qty_map[product_id] += quantity
                product_ids_from_payload.add(product_id)

        if not product_ids_from_payload:  
            logger.warning(
                "Validation Error: No product IDs found in any order_items.")
            return Response({"error": "No products found in the order."}, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            products_qs = Product.objects.filter(
                id__in=product_ids_from_payload).only("id", "name", "main_price")
        except Exception as e:  
            logger.error(
                f"Database error fetching products: {e}", exc_info=True)
            return Response({"error": "Error accessing product information."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        product_map = {p.id: p for p in products_qs}

        if len(product_map) != len(product_ids_from_payload):
            invalid_ids = product_ids_from_payload - set(product_map.keys())
            error_msg = f"Invalid product IDs: {', '.join(map(str, invalid_ids))}."
            logger.warning(f"Validation Error: {error_msg}")
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        total_amount = sum(
            Decimal(qty_map[p.id]) * p.main_price for p in product_map.values()
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        
        if total_amount <= Decimal("0.50"):
            logger.warning(
                f"Validation Error: Total amount {total_amount} is too low.")
            return Response({"error": "Total amount must be greater than 0.50."}, status=status.HTTP_400_BAD_REQUEST)

        total_cents = int(total_amount * 100)

        
        
        required_order_fields = ["shipping_address", "phone_number", "area"]
        for field in required_order_fields:
            if not payload.get(field):
                logger.warning(
                    f"Validation Error: Missing required field '{field}' in payload.")
                return Response({"error": f"'{field}' is required."}, status=status.HTTP_400_BAD_REQUEST)

        
        area_id = payload.get("area")
        try:
            area_instance = Area.objects.get(id=area_id)
        except Area.DoesNotExist:
            logger.warning(f"Validation Error: Invalid Area ID: {area_id}")
            return Response({"error": "Invalid Area ID provided."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:  
            logger.warning(
                f"Validation Error: Area ID '{area_id}' is not a valid number.")
            return Response({"error": "Area ID must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

        order_email = payload.get("email", request.user.email if hasattr(
            request.user, 'email') else None)
        if not order_email:  
            logger.warning(
                "Validation Error: Email is required for the order and was not provided or found on user profile.")
            return Response({"error": "Email is required for the order."}, status=status.HTTP_400_BAD_REQUEST)

        order = None  

        try:
            with transaction.atomic():
                logger.info("Starting atomic transaction for order creation.")
                
                order = Order.objects.create(
                    user=request.user,
                    subscription_type=payload.get(
                        "subscription_type", "weekly"),
                    shipping_address=payload.get("shipping_address"),
                    phone_number=payload.get("phone_number"),
                    
                    postal_code=payload.get("postal_code"),
                    area=area_instance,  
                    email=order_email,
                    total_amount=total_amount,
                    
                )
                logger.info(
                    f"Order {order.id} created successfully (Order Number: {order.order_number}).")

                
                for od_payload in order_data_list:
                    
                    delivery_day = od_payload.get("delivery_day")
                    if not delivery_day:  
                        logger.warning(
                            f"Order {order.id}: Validation Error: delivery_day missing in order_data item.")
                        
                        raise ValueError(
                            "delivery_day is required for each order_data item.")

                    od_instance = OrderData.objects.create(
                        order=order,
                        delivery_day=delivery_day,
                        number_of_people=od_payload.get("number_of_people", 1),
                    )
                    logger.debug(
                        f"Order {order.id}: OrderData {od_instance.id} created for delivery_day: {delivery_day}.")     
                    for item_payload in od_payload.get("order_items", []):
                        product_id = item_payload["product"]
                        product_instance = product_map.get(product_id)
                        

                        OrderItem.objects.create(
                            order_data=od_instance,
                            order=order,  
                            product=product_instance,
                            quantity=item_payload.get("quantity", 1),
                            price=product_instance.main_price,  
                        )
                        logger.debug(
                            f"Order {order.id}: OrderItem created for product {product_instance.name} (ID: {product_instance.id}).")

                logger.info(f"Order {order.id}: All database objects created.")
                logger.info(
                    f"Order {order.id}: Proceeding with Stripe customer and subscription creation.")        
                
                customer_id = get_or_create_stripe_customer(
                    request.user, email=order_email)

                logger.info(
                    f"Order {order.id}: Stripe customer ID obtained/created: {customer_id}.")
                idempotency_key = f"sub-{order.id}-{order.order_number}"

                subscription = stripe.Subscription.create(
                    customer=customer_id,
                    items=[{
                        "price_data": {
                            "currency": "eur",  
                            "product_data": {
                                "name": f"Weekly meal plan #{order.order_number} (Order ID: {order.id})",
                            },
                            "unit_amount": total_cents,
                            
                            "recurring": {"interval": "week"},
                        },
                        "quantity": 1,  
                    }],
                    payment_behavior="default_incomplete",  
                    metadata={
                        "django_order_id": order.id,
                        "django_order_number": order.order_number,
                        "django_user_id": request.user.id,
                    },
                    expand=["latest_invoice.payment_intent"],
                    
                )
                logger.info(
                    f"Order {order.id}: Stripe Subscription {subscription.id} created.")

                order.stripe_subscription_id = subscription.id
                
                order.save(update_fields=["stripe_subscription_id"])
                logger.info(
                    f"Order {order.id}: Updated with Stripe Subscription ID.")

                client_secret = None
                if subscription.latest_invoice and \
                   hasattr(subscription.latest_invoice, 'payment_intent') and \
                   subscription.latest_invoice.payment_intent and \
                   hasattr(subscription.latest_invoice.payment_intent, 'client_secret'):
                    client_secret = subscription.latest_invoice.payment_intent.client_secret
                    logger.info(
                        f"Order {order.id}: Client secret obtained for payment.")
                else:
                    logger.warning(
                        f"Order {order.id}: Stripe Subscription {subscription.id} created, but latest_invoice.payment_intent.client_secret is not available. Invoice status: {subscription.latest_invoice.status if subscription.latest_invoice else 'No invoice'}")
                
            logger.info(
                f"Order {order.id}: Successfully created subscription and local records. Responding to client.")
            return Response(
                {
                    "message": "Subscription initiated successfully.",
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "subscription_id": subscription.id,
                    "client_secret": client_secret,  
                    "total_amount": str(total_amount),
                },
                status=status.HTTP_201_CREATED,  
            )

        
        except (ValueError, Product.DoesNotExist) as e:
            logger.error(
                f"Error during order processing (User: {request.user.id}, Payload: {payload}): {type(e).__name__} - {e}", exc_info=True)
            
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            error_message = e.user_message or str(e)
            logger.error(
                f"Stripe API error during subscription creation (User: {request.user.id}, Order ID attempt: {order.id if order else 'N/A'}): {error_message}", exc_info=True)
            
            return Response({"error": f"Payment processing error: {error_message}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.critical(
                f"Unexpected critical error in CreateWeeklySubscriptionView (User: {request.user.id}, Payload: {payload}): {type(e).__name__} - {e}", exc_info=True)
            
            return Response({"error": "An unexpected server error occurred. Our team has been notified."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    
    if event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        sub_id = invoice["subscription"]
        customer_id = invoice["customer"]
        amount_paid = Decimal(invoice["amount_paid"]) / 100

        
        from .models import StripeCustomer, Order
        stripe_cust = StripeCustomer.objects.filter(
            stripe_customer_id=customer_id).first()
        if stripe_cust:
            user = stripe_cust.user
            
            order = Order.objects.filter(stripe_subscription_id=sub_id).first()
            
            Payment.objects.create(
                user=user,
                subscription=order,
                amount=amount_paid,
                is_paid=True,
                payment_type="weekly",
                payment_date=timezone.now().date(),
                transaction_id=invoice["payment_intent"],
            )
            
            print(f"[Stripe] Weekly payment OK for {user} ({amount_paid} €)")

    elif event["type"] == "invoice.payment_failed":
        
        invoice = event["data"]["object"]
        print("PAYMENT FAILED for sub", invoice["subscription"])

    return HttpResponse(status=200)




stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


class SetupCardForSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """
    Setup card for future recurring payments WITHOUT charging initially
    """

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            subscription_type = request.data.get('subscription_type', 'weekly')

            
            stripe_customer, created = StripeCustomer.objects.get_or_create(
                user=user,
                defaults={'stripe_customer_id': ''}
            )

            
            if not stripe_customer.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f"{user.first_name} {user.last_name}",
                    metadata={'user_id': user.id}
                )
                stripe_customer.stripe_customer_id = customer.id
                stripe_customer.save()

            
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer.stripe_customer_id,
                payment_method_types=['card'],
                usage='off_session',  
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
    """Confirm card setup and create subscription order"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            setup_intent_id = request.data.get('setup_intent_id')
            order_data = request.data.get('order_data')
            subscription_type = request.data.get('subscription_type', 'weekly')
            subscription_duration = request.data.get(
                'subscription_duration', '1_month')

            if not setup_intent_id:
                return Response({"error": "Setup intent ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            
            setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)

            if setup_intent['status'] not in ['succeeded', 'requires_payment_method']:
                return Response({
                    "error": f"Card setup not completed. Current status: {setup_intent['status']}."
                }, status=status.HTTP_400_BAD_REQUEST)

            
            payment_method_id = setup_intent.get('payment_method')

            
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

            
            stripe_customer = StripeCustomer.objects.get(
                stripe_customer_id=setup_intent['customer']
            )
            stripe_customer.default_payment_method_id = payment_method_id
            stripe_customer.card_last_four = payment_method['card']['last4']
            stripe_customer.card_brand = payment_method['card']['brand']
            stripe_customer.card_exp_month = payment_method['card']['exp_month']
            stripe_customer.card_exp_year = payment_method['card']['exp_year']
            stripe_customer.is_card_valid = True
            stripe_customer.save()

            
            user = request.user
            total_amount = self.calculate_order_total(user, order_data)
            print(f"Total amount calculated: {total_amount}")

            
            if subscription_duration == '1_month':
                subscription_end_date = timezone.now() + timedelta(days=30)
            elif subscription_duration == '6_months':
                subscription_end_date = timezone.now() + timedelta(days=180)
            else:
                subscription_end_date = timezone.now() + timedelta(days=30)

            print("⏰ Subscription end date:", subscription_end_date)
            with transaction.atomic():
                
                order = Order.objects.create(
                    user=request.user,
                    subscription_type=subscription_type,
                    total_amount=total_amount,
                    shipping_address=request.data.get('shipping_address', ''),
                    phone_number=request.data.get('phone_number', ''),
                    postal_code=request.data.get('postal_code', ''),
                    area_id=request.data.get('area'),
                    email=request.data.get('email', ''),
                    payment_status=False,  
                    stripe_customer_id=stripe_customer.stripe_customer_id,
                    card_saved=True,
                    is_subscription_active=True,
                    subscription_duration=subscription_duration,
                    subscription_start_date=timezone.now(),
                    subscription_end_date=subscription_end_date
                )

                print("⏰ Order created:", order)
                
                if subscription_type == 'weekly':
                    today = timezone.now()
                    current_weekday = today.weekday()  
                    if current_weekday == 0:
                        days_to_add = 7
                    else:
                        days_to_add = 7 - current_weekday
                    order.next_billing_date = today + \
                        timedelta(days=days_to_add)
                elif subscription_type == 'monthly':
                    order.next_billing_date = timezone.now() + timedelta(days=30)
                order.save()

                print("⏰ Next billing date set:", order.next_billing_date)

                
                

                for day_order in order_data:
                    delivery_day = day_order.get('delivery_day')
                    number_of_people = day_order.get('number_of_people', 1)
                    print(f"Delivery day: {delivery_day}, Number of people: {number_of_people}")

                    
                    order_data_obj = OrderData.objects.create(
                        order=order,
                        delivery_day=delivery_day,
                        number_of_people=number_of_people,
                        order_status='running',  
                    )

                    
                    for item in day_order.get('order_items', []):
                        product_id = item.get('product')
                        quantity = item.get('quantity', 1)

                        product = Product.objects.get(id=product_id)

                        
                        price = product.price
                        if number_of_people > 1:
                            price *= number_of_people

                        
                        OrderItem.objects.create(
                            order=order,
                            order_data=order_data_obj,
                            product=product,
                            product_name=product.name,
                            quantity=quantity,
                            price=price,
                        )

                print("⏰ Order items created:", order.items.all())

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
                'subscription_start_date': order.subscription_start_date,
                'subscription_end_date': order.subscription_end_date,
                'stripe_customer_id': stripe_customer.stripe_customer_id,
                'next_billing_date': order.next_billing_date,
                'card_info': {
                    'last_four': stripe_customer.card_last_four,
                    'brand': stripe_customer.card_brand,
                    'exp_month': stripe_customer.card_exp_month,
                    'exp_year': stripe_customer.card_exp_year
                }
            }, status=status.HTTP_200_OK)

        except StripeCustomer.DoesNotExist:
            return Response({"error": "Stripe customer not found."}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return Response({"error": "One or more products not found."}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
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

        
        if is_committed:
            discount_rate = Decimal('0.10')
            total *= (Decimal('1.00') - discount_rate)
            print(f"😐Total after commitment discount: {total}")

        
        delivery_charge = Decimal('1.79') * len(order_data)
        print(
            f"🚌Adding delivery charge of {delivery_charge} EUR for {len(order_data)} delivery days")
        total += delivery_charge
        print(f"✅Total after adding delivery charge: {total}")
        return total.quantize(Decimal('0.01'))


class ManageSubscriptionView(APIView):
    """Pause, resume, or cancel subscriptions"""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            action = request.data.get('action')  

            if action == 'pause':
                order.is_subscription_active = False
                order.status = 'paused'
                message = 'Subscription paused successfully'

            elif action == 'resume':
                order.is_subscription_active = True
                order.status = 'pending'
                
                if order.subscription_type == 'weekly':
                    days_ahead = 0 - timezone.now().weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    order.next_billing_date = timezone.now() + timedelta(days=days_ahead)
                else:
                    order.next_billing_date = timezone.now() + timedelta(days=30)
                message = 'Subscription resumed successfully'

            elif action == 'cancel':
                order.is_subscription_active = False
                order.status = 'cancelled'
                message = 'Subscription cancelled successfully'

            order.save()

            return Response({
                'success': True,
                'message': message,
                'subscription_status': order.is_subscription_active
            })

        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class SubscriptionDetailsView(APIView):
    """Get current subscription status and details"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)

            
            recent_payments = Payment.objects.filter(
                order=order).order_by('-payment_date')[:5]

            
            stripe_customer = StripeCustomer.objects.get(user=request.user)

            return Response({
                'order_details': {
                    'order_number': order.order_number,
                    'subscription_type': order.subscription_type,
                    'total_amount': order.total_amount,
                    'status': order.status,
                    'is_active': order.is_subscription_active,
                    'next_billing_date': order.next_billing_date,
                    'created_date': order.order_created_date,
                },
                'card_info': {
                    'last_four': stripe_customer.card_last_four,
                    'brand': stripe_customer.card_brand,
                    'exp_month': stripe_customer.card_exp_month,
                    'exp_year': stripe_customer.card_exp_year,
                },
                'recent_payments': [
                    {
                        'amount': payment.amount,
                        'status': payment.payment_status,
                        'date': payment.payment_date,
                        'billing_period': f"{payment.billing_period_start} to {payment.billing_period_end}" if payment.billing_period_start else None
                    }
                    for payment in recent_payments
                ]
            })

        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)
        except StripeCustomer.DoesNotExist:
            return Response({'error': 'Customer information not found'}, status=404)


class DeliverySchedulesAPIView(APIView):
    def get(self, request, *args, **kwargs):
        schedules = DeliverySchedule.objects.all().prefetch_related(
            'deliveryproduct_set', 'products')
        data = []

        for schedule in schedules:
            products_data = []
            delivery_products = DeliveryProduct.objects.filter(
                delivery=schedule).select_related('product')
            for dp in delivery_products:
                products_data.append({
                    'product_id': dp.product.id,
                    'product_name': dp.product.name,
                    'quantity': dp.quantity,
                    'notes': dp.notes,
                })

            schedule_dict = {
                'id': schedule.id,
                'order_id': schedule.order.id,
                'delivery_day': schedule.delivery_day,
                'status': schedule.status,
                'delivery_date': schedule.delivery_date.isoformat(),
                'area_id': schedule.area.id if schedule.area else None,
                'shipping_address': schedule.shipping_address,
                'phone_number': schedule.phone_number,
                'postal_code': schedule.postal_code,
                'email': schedule.email,
                'created_at': schedule.created_at.isoformat(),
                'updated_at': schedule.updated_at.isoformat(),
                'products': products_data,
            }
            data.append(schedule_dict)

        return Response(data)


class DeliveryScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliveryScheduleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'area', 'delivery_date']
    search_fields = ['order__order_number',
                     'shipping_address', 'postal_code', 'phone_number']

    def get_queryset(self):
        return DeliverySchedule.objects.select_related(
            'order', 'order__user', 'area'
        ).prefetch_related(
            'deliveryproduct_set__product'
        ).order_by('delivery_date', 'area__name')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        
        today = date.today()
        date_groups = defaultdict(list)

        for delivery in queryset:
            delivery_date = delivery.delivery_date
            if delivery_date == today:
                group_key = "Today"
            elif delivery_date == today + timedelta(days=1):
                group_key = "Tomorrow"
            elif today <= delivery_date <= today + timedelta(days=6):
                group_key = delivery_date.strftime("%A")  
            else:
                group_key = delivery_date.strftime("%Y-%m-%d")

            date_groups[group_key].append(delivery)

        
        sorted_groups = sorted(date_groups.items(), key=lambda x: (
            0 if x[0] == "Today" else
            1 if x[0] == "Tomorrow" else
            2 if x[0] in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] else
            3
        ))

        
        result = []
        for group_name, deliveries in sorted_groups:
            serializer = self.get_serializer(deliveries, many=True)
            result.append({
                "date_group": group_name,
                "delivery_date": deliveries[0].delivery_date.strftime("%Y-%m-%d") if deliveries else "",
                "deliveries": serializer.data,
                "total_deliveries": len(deliveries),
                "product_summary": self.get_product_summary(deliveries)
            })

        return Response(result)

    def get_product_summary(self, deliveries):
        from django.db.models import Sum
        from collections import defaultdict

        product_summary = defaultdict(int)

        for delivery in deliveries:
            for product in delivery.deliveryproduct_set.all():
                key = f"{product.product.name} (€{product.product.price})"
                product_summary[key] += product.quantity

        return dict(product_summary)


class RequestDeliveryActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DeliveryActionRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(user=request.user)  
            return success_response(message="Request submitted successfully", data=serializer.data, status=status.HTTP_200_OK)
        return failure_response(message="Failed to submit request", data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListOfRequestsView(APIView):
    permission_classes = [IsAdminOrStaff]
    pagination_class = CustomPagination

    def get(self, request):
        queryset = DeliveryActionRequest.objects.annotate(
            status_priority=Case(
                When(status='pending', then=0),
                When(status='rejected', then=1),
                When(status='approved', then=2),
                default=3,
                output_field=IntegerField()
            )
        ).order_by('status_priority', '-created_at')

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(queryset, request)
        serializer = DeliveryActionRequestSerializer(paginated_data, many=True)
        return paginator.get_paginated_response({
            "message": "Requests fetched successfully",
            "statusCode": status.HTTP_200_OK,
            "success": True,
            "data": serializer.data
        })


class AdminApproveDeliveryActionView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, request_id):
        try:
            action_request = DeliveryActionRequest.objects.get(id=request_id)
            is_pause = request.data.get('is_pause')
            order_id = request.data.get('order_id')

            if not Order.objects.filter(id=order_id).exists():
                return Response({'message': 'Order not found'}, status=404)

            order = Order.objects.get(id=order_id)

            if is_pause:
                
                duration = int(request.data.get('pause_duration_days', 3))
                order.status = 'paused'
                order.is_paused = True
                order.pause_end_date = timezone.now() + timedelta(days=duration)
            else:
                order.status = 'running'
                order.is_paused = False
                order.pause_end_date = None

            order.save()

            action_request.status = 'approved'
            action_request.save()

            return Response({"success": True, "statusCode": 200, 'message': 'Request approved and applied'}, status=200)

        except DeliveryActionRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=404)


class SubscriptionActivationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        if not order.is_subscription_expire:
            return Response({"success": False, "statusCode": 400, 'message': 'Order is not expired'}, status=400)

        
        if order.is_subscription_expire:
            now = timezone.now()
            order.subscription_start_date = now
            order.subscription_end_date = order.calculate_subscription_end_date(
                start_date=now)
            order.next_billing_date = order.get_next_billing_date()
            order.is_subscription_active = True
            order.is_paused = False  

        order.save()
        data = SubscriptionStatusSerializer(order).data

        return Response({
            "success": True,
            "statusCode": 200,
            "message": "Subscription reactivated successfully.",
            "data": data
        }, status=200)
