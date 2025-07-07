
from .models import Order, DeliverySchedule, DeliveryProduct
from datetime import timedelta
import logging
from .models import Order, Payment, StripeCustomer
import stripe
from datetime import timedelta, datetime
from django.utils import timezone
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from celery import shared_task
from django.core.mail import EmailMessage
from io import BytesIO
from datetime import timedelta, datetime, date
from .models import OrderData
from django.db.models import Q
from django.conf import settings
from subscriptions.models import FreeBoxRequest
from dateutil.relativedelta import relativedelta
from auths.models import CommitmentForSixMonths
from products.models import Product
from decimal import Decimal
import calendar
from collections import defaultdict
from .serializers import OrderDataSerializer

from celery import shared_task
from django.utils import timezone
from .models import Order


@shared_task
def mark_expired_subscriptions():
    now = timezone.now()
    orders = Order.objects.filter(
        is_subscription_active=True,
        is_subscription_expire=False,
        subscription_end_date__lt=now
    )
    for order in orders:
        order.is_subscription_expire = True
        order.is_subscription_active = False
        order.save()


@shared_task
def auto_resume_orders():
    now = timezone.now()
    paused_orders = Order.objects.filter(
        is_paused=True, pause_end_date__lte=now)

    for order in paused_orders:
        order.is_paused = False
        order.status = 'running'
        order.pause_end_date = None
        order.save()
        print("✅ Order resumed:", order.id)


def send_email_with_body(subject, body, pdf_buffer=None):
    try:
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.BEKARY_EMAIL],
        )
        if pdf_buffer:
            email.attach("product_list.pdf",
                         pdf_buffer.read(), "application/pdf")
        email.send()
        print("PDF successfully sent to bakery.")
    except Exception as e:
        print(f"Error sending email: {e}")


def generate_product_pdf(table_data, future_date, total_orders, total_products):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    day_name = future_date.strftime('%A')  
    date_str = future_date.strftime('%B %d, %Y')  

    company_name = "Preisslers Frühstück"
    header_text = f"{company_name} - {day_name}, {date_str} - Product List"

    styles = getSampleStyleSheet()
    header_style = styles['Title']
    header_style.fontSize = 16
    header_paragraph = Paragraph(header_text, header_style)
    elements.append(header_paragraph)
    summary_text = f"Total Orders: {total_orders} | Total Products: {total_products}"
    summary_style = styles['Normal']
    summary_style.fontSize = 12
    summary_paragraph = Paragraph(summary_text, summary_style)
    elements.append(summary_paragraph)
    elements.append(Paragraph("<br/>", styles['Normal']))  

    
    header = ['Product Name', 'Quantity']

    
    table_data_with_total = table_data + [['TOTAL', str(total_products)]]
    table = Table([header] + table_data_with_total)

    
    style = TableStyle([
        
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.black),  
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  

        
        ('BACKGROUND', (0, -1), (-1, -1), colors.gold),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('GRID', (0, -1), (-1, -1), 2, colors.black),
    ])
    table.setStyle(style)
    elements.append(table)

    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def get_next_delivery_date_for_day(target_day_name):
    """Calculate the next delivery date for a specific day name"""
    today = date.today()
    day_index_today = today.weekday()
    day_name_list = list(calendar.day_name)

    
    target_index = day_name_list.index(target_day_name)

    
    days_ahead = (target_index - day_index_today + 7) % 7
    if days_ahead == 0:  
        days_ahead = 7

    next_delivery_date = today + timedelta(days=days_ahead)
    return next_delivery_date


def get_production_data_for_day(target_date, target_day_name):
    """Get production data for a specific day and date"""

    
    order_data_list = OrderData.objects.select_related('order').prefetch_related(
        'order_items'
    ).filter(
        delivery_day=target_day_name,
        is_cancelled=False,
        order_status='pending'
    )

    
    free_box_requests = FreeBoxRequest.objects.filter(
        date_of_delivery=target_date
    )

    product_quantity = defaultdict(int)
    total_orders = 0

    
    today = date.today()
    day_index_today = today.weekday()
    day_name_list = list(calendar.day_name)

    for order_data in order_data_list:
        serialized_order_data = OrderDataSerializer(order_data).data

        
        target_index = day_name_list.index(target_day_name)
        days_ahead = (target_index - day_index_today + 7) % 7 or 7
        calculated_delivery_date = today + timedelta(days=days_ahead)

        
        if calculated_delivery_date == target_date:
            total_orders += 1

            
            for item in serialized_order_data['order_items']:
                product_name = item['product_name']
                quantity = item['quantity'] * \
                    serialized_order_data['number_of_people']
                product_quantity[product_name] += quantity

    
    for free_req in free_box_requests:
        total_orders += 1
        box = free_req.box
        people = free_req.number_of_people

        for product in box.items.all():
            product_name = product.name
            quantity = people  
            product_quantity[product_name] += quantity

    return product_quantity, total_orders


@shared_task
def send_daily_product_list_email():
    """
    Send daily product list email 3 days in advance
    Combines day-wise orders with date-specific free deliveries
    """
    try:
        
        today_date = date.today()
        future_date = today_date + timedelta(days=3)
        future_day = future_date.strftime('%A')

        print(f"Generating product list for {future_day} ({future_date})")

        
        product_quantity, total_orders = get_production_data_for_day(
            future_date, future_day)

        
        table_data = [[product_name, quantity]
                      for product_name, quantity in sorted(product_quantity.items())]

        
        total_products = sum(product_quantity.values())

        
        print(f"Total Orders: {total_orders}")
        print(f"Total Products: {total_products}")
        for product_name, quantity in product_quantity.items():
            print(f"{product_name}: {quantity}")

        
        email_subject = f"Produktliste für {future_day} ({future_date})"
        email_body = f"Produktliste für {future_day} ({future_date})\n\n"
        email_body += f"Gesamtbestellungen: {total_orders}\n"
        email_body += f"Gesamtprodukte: {total_products}\n\n"

        if table_data:
            email_body += "Produktdetails:\n"
            email_body += "\n".join(
                [f"{row[0]} x {row[1]}" for row in table_data])

            
            pdf_buffer = generate_product_pdf(
                table_data, future_date, total_orders, total_products
            )

            
            send_email_with_body(email_subject, email_body, pdf_buffer)
            print(f"Product list sent successfully for {future_day}")

        else:
            
            email_body += f"Keine Produkte verfügbar für {future_day} ({future_date})."
            send_email_with_body(email_subject, email_body)
            print(f"No products found for {future_day}")

        return f"Email sent for {future_day} - {total_orders} orders, {total_products} products"

    except Exception as e:
        print(f"Error in send_daily_product_list_email: {str(e)}")
        raise e


@shared_task
def send_product_list_for_specific_day(days_ahead=3):
    """
    Send product list for a specific number of days ahead
    Useful for manual triggers or testing
    """
    try:
        today_date = date.today()
        future_date = today_date + timedelta(days=days_ahead)
        future_day = future_date.strftime('%A')

        product_quantity, total_orders = get_production_data_for_day(
            future_date, future_day)

        table_data = [[product_name, quantity]
                      for product_name, quantity in sorted(product_quantity.items())]

        total_products = sum(product_quantity.values())

        email_subject = f"Produktliste für {future_day} ({future_date})"
        email_body = f"Produktliste für {future_day} ({future_date})\n\n"
        email_body += f"Gesamtbestellungen: {total_orders}\n"
        email_body += f"Gesamtprodukte: {total_products}\n\n"

        if table_data:
            email_body += "Produktdetails:\n"
            email_body += "\n".join(
                [f"{row[0]} x {row[1]}" for row in table_data])

            pdf_buffer = generate_product_pdf(
                table_data, future_date, total_orders, total_products
            )
            send_email_with_body(email_subject, email_body, pdf_buffer)
        else:
            email_body += f"Keine Produkte verfügbar für {future_day} ({future_date})."
            send_email_with_body(email_subject, email_body)

        return f"Email sent for {future_day} ({days_ahead} days ahead)"

    except Exception as e:
        print(f"Error in send_product_list_for_specific_day: {str(e)}")
        raise e

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


@shared_task
def charge_monthly_subscriptions():
    """Charge all monthly subscriptions and deactivate expired ones first."""
    today = timezone.now().date()

    
    expired_orders = Order.objects.filter(
        is_subscription_active=True,
        is_subscription_expire=False,
        subscription_end_date__lt=today
    )
    expired_orders.update(is_subscription_active=False)

    
    monthly_orders = Order.objects.filter(
        subscription_type='monthly',
        is_subscription_active=True,
        is_subscription_expire=False,
        card_saved=True,
        next_billing_date=today
    )

    return process_subscription_charges(monthly_orders, 'monthly')


logger = logging.getLogger(__name__)


@shared_task
def charge_weekly_subscriptions():
    """
    CORRECTED version with the exact fixes needed
    """
    logger.info("🔄 Starting charge_weekly_subscriptions task")
    today = timezone.now().date()
    logger.info(f"📅 Today's date: {today}")

    
    all_weekly_orders = Order.objects.filter(subscription_type='weekly')
    logger.info(
        f"📊 Total weekly orders in system: {all_weekly_orders.count()}")

    
    active_weekly = Order.objects.filter(
        subscription_type='weekly',
        is_subscription_active=True,
        is_subscription_expire=False,
    )
    logger.info(f"✅ Active weekly subscriptions: {active_weekly.count()}")

    

    pause_weekly = Order.objects.filter(
        subscription_type='weekly',
        is_subscription_active=True,
        is_subscription_expire=False,
        is_paused=False
    )
    logger.info(f"🚫 Not paused weekly subscriptions: {pause_weekly.count()}")

    
    with_cards = Order.objects.filter(
        subscription_type='weekly',
        is_subscription_active=True,
        is_subscription_expire=False,
        is_paused=False,
        card_saved=True
    )
    logger.info(f"💳 Active weekly with saved cards: {with_cards.count()}")

    
    due_today = Order.objects.filter(
        subscription_type='weekly',
        is_subscription_active=True,
        is_subscription_expire=False,
        is_paused=False,
        card_saved=True,
        next_billing_date=today
    )
    logger.info(f"⏰ Orders due today: {due_today.count()}")

    
    weekly_orders = Order.objects.filter(
        subscription_type='weekly',
        is_subscription_active=True,
        is_subscription_expire=False,
        is_paused=False,
        card_saved=True,
        next_billing_date=today
    ).filter(
        Q(subscription_end_date__isnull=True) |  
        Q(subscription_end_date__gte=timezone.now())  
    )
    logger.info(f"🎯 Final filtered orders to process: {weekly_orders.count()}")

    
    for order in weekly_orders:
        logger.info(f"📋 Order {order.order_number}:")
        logger.info(f"   - User: {order.user.email}")
        logger.info(f"   - Next billing: {order.next_billing_date}")
        logger.info(f"   - End date: {order.subscription_end_date}")
        logger.info(f"   - Active: {order.is_subscription_active}")
        logger.info(f"   - Card saved: {order.card_saved}")

    charged_orders = []

    for order in weekly_orders:
        try:
            logger.info(f"💰 Processing order {order.order_number}")

            
            next_billing = order.next_billing_date + timedelta(days=7)
            logger.info(f"   Next billing will be: {next_billing}")

            
            if order.subscription_end_date is not None:
                if next_billing.date() > order.subscription_end_date.date():
                    logger.info(
                        f"   ❌ Subscription expired for {order.order_number}")
                    order.is_subscription_active = False
                    order.save()
                    continue
            else:
                logger.info(
                    f"   ✅ No end date - subscription continues indefinitely")

            
            
            valid_days = order.order_data.filter(
                is_paused=False,
                is_cancelled=False
            )
            logger.info(f"   📅 Valid delivery days: {valid_days.count()}")

            
            if not valid_days.exists():
                logger.info(
                    f"   ⚠️ No valid delivery days for {order.order_number}")
                continue

            
            order_data = []
            for day in valid_days:
                day_dict = {
                    'number_of_people': getattr(day, 'number_of_people', 1),
                    'order_items': []
                }

                order_items = day.order_items.all()
                logger.info(
                    f"   🛒 Day {day.delivery_day} has {order_items.count()} items")

                for item in order_items:
                    day_dict['order_items'].append({
                        'product': item.product.id,
                        'quantity': item.quantity,
                    })

                order_data.append(day_dict)

            
            total_amount = calculate_order_total(order.user, order_data)
            logger.info(f"   💵 Calculated total: €{total_amount}")

            if total_amount == 0:
                logger.info(
                    f"   ⚠️ Total amount is 0 for {order.order_number}")
                continue

            
            order.total_amount = total_amount
            order.next_billing_date = next_billing
            order.save()

            charged_orders.append(order.id)
            logger.info(
                f"   ✅ Order {order.order_number} prepared for charging")

        except Exception as e:
            logger.error(
                f"   ❌ Error processing order {order.order_number}: {str(e)}")
            import traceback
            logger.error(f"   📋 Full traceback: {traceback.format_exc()}")
            continue

    logger.info(f"🎯 Total orders prepared for charging: {len(charged_orders)}")

    
    if charged_orders:
        valid_orders = Order.objects.filter(id__in=charged_orders)
        result = process_subscription_charges(
            valid_orders, subscription_type='weekly')
        logger.info(f"💳 Charging result: {result}")
    else:
        result = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'total_amount': 0,
            'errors': ['No orders to process']
        }

    
    try:
        expired_count = Order.objects.filter(
            is_subscription_active=True,
            is_subscription_expire=False,
            subscription_end_date__isnull=False,  
            subscription_end_date__lt=timezone.now()
        ).update(is_subscription_active=False)
        logger.info(f"🔚 Deactivated {expired_count} expired subscriptions")
    except Exception as e:
        logger.error(f"❌ Error in cleanup: {str(e)}")

    return result


def calculate_order_total(user, order_data):
    """
    Fixed calculate_order_total function (this was a method, now it's a function)
    """
    try:
        from auths.models import CommitmentForSixMonths
        from products.models import Product

        is_committed = CommitmentForSixMonths.objects.filter(
            user=user, commitment_status=True).exists()

        total = Decimal('0.00')
        logger.info(
            f"💰 Calculating total for user {user.id} with commitment: {is_committed}")

        for day_order in order_data:
            number_of_people = int(day_order.get('number_of_people', 1))
            logger.info(f"   👥 Number of people: {number_of_people}")

            for item in day_order.get('order_items', []):
                product_id = item.get('product')
                quantity = int(item.get('quantity', 1))

                try:
                    product = Product.objects.get(id=product_id)
                    price = product.price

                    if number_of_people > 1:
                        price *= number_of_people

                    item_total = price * quantity
                    total += item_total

                    logger.info(
                        f"   🛒 Product {product.name}: {quantity} x €{price} = €{item_total}")

                except Product.DoesNotExist:
                    logger.error(f"   ❌ Product {product_id} not found")
                    continue

        logger.info(f"   💵 Subtotal: €{total}")

        
        if is_committed:
            discount_rate = Decimal('0.10')
            discount_amount = total * discount_rate
            total *= (Decimal('1.00') - discount_rate)
            logger.info(f"   🎯 Commitment discount (10%): -€{discount_amount}")
            logger.info(f"   💵 After discount: €{total}")

        
        delivery_charge = Decimal('1.79') * len(order_data)
        total += delivery_charge

        logger.info(
            f"   🚚 Delivery charge: €{delivery_charge} ({len(order_data)} days)")
        logger.info(f"   ✅ Final total: €{total}")

        return total.quantize(Decimal('0.01'))

    except Exception as e:
        logger.error(f"❌ Error calculating order total: {str(e)}")
        return Decimal('0.00')


def process_subscription_charges(orders, subscription_type):
    """Enhanced process_subscription_charges with better error handling"""
    results = {
        'processed': 0,
        'successful': 0,
        'failed': 0,
        'total_amount': 0,
        'errors': []
    }

    logger.info(
        f"💳 Processing charges for {orders.count()} {subscription_type} orders")

    for order in orders:
        try:
            results['processed'] += 1
            logger.info(f"💰 Processing payment for order {order.order_number}")

            
            try:
                stripe_customer = StripeCustomer.objects.get(user=order.user)
                logger.info(
                    f"   ✅ Stripe customer found: {stripe_customer.stripe_customer_id}")
            except StripeCustomer.DoesNotExist:
                error_msg = f"No Stripe customer for order {order.order_number}"
                logger.error(f"   ❌ {error_msg}")
                results['failed'] += 1
                results['errors'].append(error_msg)
                continue

            if not stripe_customer.default_payment_method_id:
                error_msg = f"No payment method for order {order.order_number}"
                logger.error(f"   ❌ {error_msg}")
                results['failed'] += 1
                results['errors'].append(error_msg)
                continue

            billing_start = order.next_billing_date

            if subscription_type == 'weekly':
                billing_end = billing_start + timedelta(weeks=1)
                next_billing = billing_start + timedelta(weeks=1)
            else:  
                from dateutil.relativedelta import relativedelta
                billing_end = billing_start + relativedelta(months=1)
                next_billing = billing_start + relativedelta(months=1)

            
            if order.subscription_end_date and next_billing.date() > order.subscription_end_date:
                order.is_subscription_active = False
                order.save()
                error_msg = f"Subscription expired for order {order.order_number}"
                logger.error(f"   ❌ {error_msg}")
                results['errors'].append(error_msg)
                continue

            logger.info(
                f"   💳 Creating payment intent for €{order.total_amount}")

            
            payment_intent = stripe.PaymentIntent.create(
                amount=int(order.total_amount * 100),  
                currency='eur',
                customer=stripe_customer.stripe_customer_id,
                payment_method=stripe_customer.default_payment_method_id,
                off_session=True,
                confirm=True,
                description=f"Subscription payment for order #{order.order_number}",
                metadata={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'subscription_type': subscription_type,
                    'billing_period': f"{billing_start.date()} to {billing_end.date()}"
                }
            )

            logger.info(
                f"   💳 Payment intent status: {payment_intent['status']}")

            if payment_intent['status'] == 'succeeded':
                
                Payment.objects.create(
                    user=order.user,
                    order=order,
                    amount=order.total_amount,
                    payment_type=subscription_type,
                    payment_status='succeeded',
                    stripe_payment_intent_id=payment_intent.id,
                    billing_period_start=billing_start,
                    billing_period_end=billing_end
                )

                
                order.next_billing_date = next_billing
                order.payment_date = timezone.now()
                order.save()

                results['successful'] += 1
                results['total_amount'] += float(order.total_amount)

                logger.info(
                    f"   ✅ Payment succeeded for order {order.order_number}")

                
                send_payment_success_email.delay(order.id, payment_intent.id)

            else:
                results['failed'] += 1
                error_msg = f"Payment failed for order {order.order_number}: {payment_intent['status']}"
                results['errors'].append(error_msg)
                logger.error(f"   ❌ {error_msg}")

                
                Payment.objects.create(
                    user=order.user,
                    order=order,
                    amount=order.total_amount,
                    payment_type=subscription_type,
                    payment_status='failed',
                    stripe_payment_intent_id=payment_intent.id,
                    billing_period_start=billing_start,
                    billing_period_end=billing_end,
                    failure_reason=payment_intent['status']
                )

        except stripe.error.CardError as e:
            results['failed'] += 1
            error_msg = f"Card declined for order {order.order_number}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"   ❌ {error_msg}")

            
            Payment.objects.create(
                user=order.user,
                order=order,
                amount=order.total_amount,
                payment_type=subscription_type,
                payment_status='failed',
                billing_period_start=billing_start,
                billing_period_end=billing_end,
                failure_reason=str(e)
            )

            
            send_payment_failure_email.delay(order.id, str(e))

        except Exception as e:
            results['failed'] += 1
            error_msg = f"Error processing order {order.order_number}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"   ❌ {error_msg}")

    logger.info(f"💳 Charging complete: {results}")
    return results


@shared_task
def send_payment_success_email(order_id, payment_id):
    """Send email for successful payment"""
    try:
        from django.core.mail import EmailMessage
        from django.conf import settings

        order = Order.objects.get(id=order_id)
        payment = Payment.objects.get(id=payment_id)

        subject = f"Payment Successful - Order #{order.order_number}"
        message = f"""
        Dear {order.user.first_name or order.user.username},

        Your {payment.payment_type} subscription payment has been processed successfully.

        Payment Details:
        - Order Number: #{order.order_number}
        - Amount: €{payment.amount}
        - Payment Date: {payment.payment_date.strftime('%Y-%m-%d %H:%M')}
        - Billing Period: {payment.billing_period_start.strftime('%Y-%m-%d')} to {payment.billing_period_end.strftime('%Y-%m-%d')}
        - Next Payment: {order.next_billing_date.strftime('%Y-%m-%d')}

        Delivery Address: {order.shipping_address}

        Thank you for your continued subscription!

        Best regards,
        Your Company Team
        """

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email or order.user.email]
        )
        email.send()
        print("Success email sent successfully.---------------------------celery beat")
        return f"Success email sent for order {order.order_number}"

    except Exception as e:
        return f"Failed to send success email: {str(e)}"


@shared_task
def send_payment_failure_email(order_id, failure_reason):
    """Send email for failed payment"""
    try:
        from django.core.mail import EmailMessage
        from django.conf import settings

        order = Order.objects.get(id=order_id)

        subject = f"Payment Failed - Order #{order.order_number}"
        message = f"""
        Dear {order.user.first_name or order.user.username},

        We were unable to process your subscription payment.

        Order Details:
        - Order Number: #{order.order_number}
        - Amount: €{order.total_amount}
        - Reason: {failure_reason}

        Please update your payment method or contact us to resolve this issue.
        Your subscription will be paused until payment is resolved.

        Best regards,
        Your Company Team
        """

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.email or order.user.email]
        )
        email.send()
        print("Failure email sent successfully.---------------------------celery beat")
        return f"Failure email sent for order {order.order_number}"

    except Exception as e:
        return f"Failed to send failure email: {str(e)}"

    
@shared_task
def generate_delivery_schedules_and_reports():
    today = timezone.now().date()

    
    for day_offset in range(3):
        delivery_date = today + timedelta(days=day_offset)
        weekday_name = delivery_date.strftime('%A')

        
        orders = Order.objects.filter(
            subscription_type='weekly',
            is_subscription_active=True,
            is_subscription_expire=False,
            is_paused=False,
            subscription_end_date__gte=delivery_date,
            order_data__delivery_day__iexact=weekday_name,
            order_data__is_paused=False,
            order_data__is_cancelled=False
        ).distinct()

        for order in orders:
            
            order_data = order.order_data.filter(
                delivery_day__iexact=weekday_name,
                is_paused=False,
                is_cancelled=False
            ).first()

            if not order_data:
                continue

            
            delivery_schedule, created = DeliverySchedule.objects.get_or_create(
                order=order,
                delivery_date=delivery_date,
                defaults={
                    'delivery_day': weekday_name,
                    'status': 'pending',
                    'area': order.area,
                    'shipping_address': order.shipping_address,
                    'phone_number': order.phone_number,
                    'postal_code': order.postal_code,
                    'email': order.user.email if order.user else order.email
                }
            )

            
            delivery_schedule.products.clear()
            for item in order_data.order_items.all():
                DeliveryProduct.objects.create(
                    delivery=delivery_schedule,
                    product=item.product,
                    quantity=item.quantity * order_data.number_of_people,
                    notes=''
                )

    return "Delivery schedules and reports generated successfully"
