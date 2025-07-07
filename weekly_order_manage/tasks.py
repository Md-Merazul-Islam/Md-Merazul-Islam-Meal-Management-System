from django.db.models import Prefetch
from subscriptions.models import FreeBoxRequest
from weekly_order_manage.models import DeliveryDay, DeliveryItem
import traceback
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import letter
from django.core.mail import EmailMessage
from datetime import date, timedelta
from django.core.mail import send_mail
from collections import defaultdict
from auths.models import CommitmentForSixMonths
from celery import shared_task
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import stripe
from django.conf import settings
import logging
from django.db.models import Q
from .models import Order, DeliveryDay, Payment, StripeCustomer

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
# ===============================================================================================================================================================


# Import your models (adjust imports based on your project structure)

# Set up logger
logger = logging.getLogger('product_list_email')


def send_email_with_body(subject, body, pdf_buffer=None):
    """Send email with optional PDF attachment"""
    logger.info(f"Attempting to send email with subject: {subject}")

    try:
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.BEKARY_EMAIL],
        )

        if pdf_buffer:
            logger.info("Attaching PDF to email")
            email.attach("product_list.pdf",
                         pdf_buffer.read(), "application/pdf")

        email.send()
        logger.info(f"Email successfully sent to {settings.BEKARY_EMAIL}")
        return True

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        logger.error(f"Email subject: {subject}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def generate_product_pdf(table_data, target_date, total_orders, total_products, product_details):
    """Generate PDF with product list and detailed breakdown"""
    logger.info(f"Starting PDF generation for date: {target_date}")
    logger.info(
        f"PDF data - Orders: {total_orders}, Products: {total_products}")

    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Header information
        day_name = target_date.strftime('%A')
        date_str = target_date.strftime('%B %d, %Y')
        company_name = "Preisslers Frühstück"
        header_text = f"{company_name} - {day_name}, {date_str} - Product List"

        logger.debug(f"PDF header: {header_text}")

        # Set up styles
        styles = getSampleStyleSheet()
        header_style = styles['Title']
        header_style.fontSize = 14
        header_paragraph = Paragraph(header_text, header_style)
        elements.append(header_paragraph)

        # Add summary information
        # NEED 2 NEW LINE GAP
        summary_text = f" Total Products: {total_products}"
        summary_style = styles['Normal']
        summary_style.fontSize = 12
        summary_paragraph = Paragraph(summary_text, summary_style)
        elements.append(summary_paragraph)
        elements.append(Paragraph("<br/> <br/> ", styles['Normal']))

        # Main product table
        if table_data:
            logger.info(f"Adding {len(table_data)} products to PDF table")
            header = ['Product Name', 'Total Quantity']
            table_data_with_total = table_data + \
                [['TOTAL PRODUCTS', str(total_products)]]
            table = Table([header] + table_data_with_total)

            # Table styling

            # Table styling
            style = TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                # Cell styling
                ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                # ('TOPPADDING', (0, 0), (-1, -1),5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

                # Total row styling
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('GRID', (0, -1), (-1, -1), 2, colors.black),
            ])
            table.setStyle(style)
            elements.append(table)

        else:
            # No products message
            logger.warning(
                f"No products found for {target_date}, adding empty message to PDF")
            no_products_text = f"No products scheduled for delivery on {day_name}, {date_str}"
            no_products_paragraph = Paragraph(
                no_products_text, styles['Normal'])
            elements.append(no_products_paragraph)

        # Build the PDF
        logger.info("Building PDF document")
        doc.build(elements)
        buffer.seek(0)

        logger.info(
            f"PDF successfully generated. Size: {len(buffer.getvalue())} bytes")
        return buffer

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise e


def get_production_data_for_date(target_date):
    """
    Get all production data for a specific target date
    Includes both regular delivery orders and free box requests
    """
    logger.info(
        f"=== Starting production data calculation for: {target_date} ===")

    product_quantity = defaultdict(int)
    total_orders = 0
    product_details = {
        'regular_orders': [],
        'free_boxes': []
    }

    try:
        # 1. Get Regular Delivery Orders for the target date
        logger.info("Querying regular delivery orders...")

        delivery_days = DeliveryDay.objects.prefetch_related(Prefetch(
            'order_items', queryset=DeliveryItem.objects.select_related('product'))).filter(delivery_date=target_date)
        logger.info(
            f"Found {delivery_days.count()} regular delivery days for {target_date}")

        for delivery_day in delivery_days:
            try:
                order = delivery_day.week.order

                logger.debug(
                    f"Processing delivery day: {delivery_day.day_name} for order {order.order_number}")

                # Skip if order is not active
                # if not hasattr(order, 'status') or order.status != 'active':
                #     logger.warning(f"Skipping order {order.order_number} - inactive or missing status")
                #     continue

                total_orders += 1
                # Default to 1 if None
                people_count = getattr(
                    delivery_day, 'number_of_people', 1) or 1

                logger.debug(
                    f"Order {order.order_number}: {people_count} people")

                # Add to details for breakdown
                product_details['regular_orders'].append({
                    'order_number': getattr(order, 'order_number', 'Unknown'),
                    'people': people_count,
                    'day': getattr(delivery_day, 'day_name', 'Unknown'),
                    'delivery_date': delivery_day.delivery_date
                })

                # Calculate product quantities for this delivery
                # Try different possible related names for delivery items
                delivery_items = None
                for attr_name in ['deliveryitem_set', 'order_items', 'items']:
                    if hasattr(delivery_day, attr_name):
                        delivery_items = getattr(delivery_day, attr_name).all()
                        logger.debug(
                            f"Found delivery items using: {attr_name}")
                        break

                if delivery_items:
                    for delivery_item in delivery_items:
                        try:
                            product = delivery_item.product
                            product_name = getattr(
                                product, 'name', f'Product #{product.id}')
                            base_quantity = getattr(
                                delivery_item, 'quantity', 1) or 1

                            # Quantity = base quantity × number of people
                            total_quantity = base_quantity * people_count
                            product_quantity[product_name] += total_quantity

                            logger.debug(
                                f"  Regular: {product_name} = {base_quantity} × {people_count} = {total_quantity}")
                        except Exception as item_error:
                            logger.warning(
                                f"Error processing delivery item: {item_error}")
                            continue
                else:
                    logger.warning(
                        f"No delivery items found for delivery day {delivery_day.id}")

            except Exception as day_error:
                logger.warning(
                    f"Error processing delivery day {delivery_day.id}: {day_error}")
                continue

        logger.info(
            f"Regular orders processed: {len(product_details['regular_orders'])} orders")

        # 2. Get Free Box Requests for the target date
        logger.info("Querying free box requests...")
        try:
            free_box_requests = FreeBoxRequest.objects.select_related(
                'box'
            ).prefetch_related(
                'box__items'
            ).filter(
                date_of_delivery=target_date
            ).exclude(
                delivery_status=True  # Exclude already delivered
            )

            logger.info(
                f"Found {free_box_requests.count()} free box requests for {target_date}")

            for free_request in free_box_requests:
                try:
                    total_orders += 1
                    people_count = getattr(
                        free_request, 'number_of_people', 1) or 1
                    box = free_request.box

                    if not box:
                        logger.warning(
                            f"Free request {free_request.id} has no associated box")
                        continue

                    logger.debug(
                        f"Processing free box: {box.name} for {people_count} people (Requester: {getattr(free_request, 'name', 'Unknown')})")

                    # Add to details for breakdown
                    product_details['free_boxes'].append({
                        'box_name': getattr(box, 'name', 'Unknown Box'),
                        'people': people_count,
                        'name': getattr(free_request, 'name', 'Unknown'),
                        'delivery_date': free_request.date_of_delivery
                    })

                    # Calculate product quantities for this free box
                    box_items = box.items.all() if hasattr(box, 'items') else []

                    for product in box_items:
                        try:
                            product_name = getattr(
                                product, 'name', f'Product #{product.id}')
                            # Get quantity per person from box item (if available) or default to 1
                            quantity_per_person = 1
                            if hasattr(product, 'quantity'):
                                quantity_per_person = getattr(
                                    product, 'quantity', 1) or 1

                            total_quantity = quantity_per_person * people_count
                            product_quantity[product_name] += total_quantity

                            logger.debug(
                                f"  Free Box: {product_name} = {quantity_per_person} × {people_count} = {total_quantity}")
                        except Exception as product_error:
                            logger.warning(
                                f"Error processing box product: {product_error}")
                            continue

                except Exception as request_error:
                    logger.warning(
                        f"Error processing free box request {free_request.id}: {request_error}")
                    continue

        except Exception as free_box_error:
            logger.error(f"Error querying free box requests: {free_box_error}")
            # Continue without free boxes rather than failing completely

        logger.info(
            f"Free box requests processed: {len(product_details['free_boxes'])} requests")

        # Log final summary
        total_products = sum(product_quantity.values())
        logger.info(f"=== Production Summary for {target_date} ===")
        logger.info(f"Total Orders: {total_orders}")
        logger.info(f"Total Products: {total_products}")
        logger.info(f"Unique Product Types: {len(product_quantity)}")

        if product_quantity:
            logger.info(f"Product breakdown:")
            for product_name, quantity in sorted(product_quantity.items()):
                logger.info(f"  {product_name}: {quantity}")
        else:
            logger.info("No products found for this date")

        return product_quantity, total_orders, product_details

    except Exception as e:
        logger.error(
            f"Critical error getting production data for {target_date}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Return empty data rather than failing completely
        logger.warning("Returning empty production data due to error")
        return defaultdict(int), 0, {'regular_orders': [], 'free_boxes': []}


@shared_task
def send_daily_product_list_email():
    """
    Celery task to send daily product list email 3 days in advance
    Combines regular delivery orders with free box requests
    """
    task_start_time = date.today()
    logger.info(
        f"=== Starting daily product list email task at {task_start_time} ===")

    try:
        # Calculate target date (3 days from today)
        today_date = date.today()
        target_date = today_date + timedelta(days=3)
        day_name = target_date.strftime('%A')

        logger.info(f"Task parameters:")
        logger.info(f"  Today: {today_date}")
        logger.info(f"  Target date: {target_date} ({day_name})")
        logger.info(f"  Days in advance: 3")

        # Get all production data for the target date
        logger.info("Starting production data retrieval...")
        product_quantity, total_orders, product_details = get_production_data_for_date(
            target_date)

        # Convert to sorted table data
        table_data = [
            [product_name, quantity]
            for product_name, quantity in sorted(product_quantity.items())
        ]

        # Calculate totals
        total_products = sum(product_quantity.values())

        # Log summary
        logger.info(f"=== Task Summary ===")
        logger.info(f"Target date: {target_date} ({day_name})")
        logger.info(f"Total orders found: {total_orders}")
        logger.info(
            f"Regular delivery orders: {len(product_details['regular_orders'])}")
        logger.info(f"Free box requests: {len(product_details['free_boxes'])}")
        logger.info(f"Total products needed: {total_products}")
        logger.info(f"Unique product types: {len(product_quantity)}")

        # Prepare email content
        email_subject = f"Produktliste für {day_name} ({target_date})"
        logger.info(f"Preparing email with subject: {email_subject}")

        # Build email body
        email_body = f"Produktliste für {day_name} ({target_date})\n\n"
        # email_body += f"Gesamtbestellungen: {total_orders}\n"
        email_body += f"Gesamtprodukte: {total_products}\n\n"

        if table_data:
            logger.info(f"Building email with {len(table_data)} product types")
            email_body += "Produktdetails:\n"
            email_body += "\n".join(
                [f"•▶ {row[0]}: {row[1]} Stück" for row in table_data])
            email_body += "\n\n"

            # Generate and send PDF
            logger.info("Generating PDF attachment...")
            pdf_buffer = generate_product_pdf(
                table_data, target_date, total_orders, total_products, product_details
            )

            logger.info("Sending email with PDF attachment...")
            success = send_email_with_body(
                email_subject, email_body, pdf_buffer)

            if success:
                result_message = f"Product list sent successfully for {day_name} ({target_date})"
                result_message += f" - {total_orders} orders, {total_products} products"
                logger.info(f"=== TASK COMPLETED SUCCESSFULLY ===")
                logger.info(result_message)
                return result_message
            else:
                error_message = "Failed to send email with PDF"
                logger.error(error_message)
                raise Exception(error_message)

        else:
            # No products case
            logger.warning(f"No products found for {day_name} ({target_date})")
            email_body += f"Keine Produkte für Lieferung am {day_name} ({target_date}) geplant."

            logger.info("Sending no-products email...")
            success = send_email_with_body(email_subject, email_body)

            if success:
                result_message = f"No products email sent for {day_name} ({target_date})"
                logger.info(f"=== TASK COMPLETED (NO PRODUCTS) ===")
                logger.info(result_message)
                return result_message
            else:
                error_message = "Failed to send no-products email"
                logger.error(error_message)
                raise Exception(error_message)

    except Exception as e:
        error_message = f"Error in send_daily_product_list_email: {str(e)}"
        logger.error(f"=== TASK FAILED ===")
        logger.error(error_message)
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Send error notification email
        try:
            logger.info("Attempting to send error notification email...")
            error_subject = f"ERROR: Produktliste Generierung fehlgeschlagen - {date.today()}"
            error_body = f"Fehler beim Generieren der Produktliste für {target_date}:\n\n"
            error_body += f"Fehler: {str(e)}\n\n"
            error_body += f"Vollständiger Traceback:\n{traceback.format_exc()}"

            error_sent = send_email_with_body(error_subject, error_body)
            if error_sent:
                logger.info("Error notification email sent successfully")
            else:
                logger.error("Failed to send error notification email")

        except Exception as email_error:
            logger.error(f"Failed to send error notification: {email_error}")

    raise e


# Performance monitoring decorator
def log_performance(func):
    """Decorator to log function performance"""
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        logger.info(f"Starting {func.__name__}")

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"{func.__name__} completed in {duration:.2f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(
                f"{func.__name__} failed after {duration:.2f} seconds: {e}")
            raise e

    return wrapper


# Enhanced task with performance monitoring
@shared_task
@log_performance
def send_daily_product_list_email_with_monitoring():
    """
    Enhanced version with performance monitoring
    """
    return send_daily_product_list_email()


# Health check function
def health_check_product_list_system():
    """
    Health check function to verify system components
    """
    logger.info("=== Product List System Health Check ===")

    health_status = {
        'database_connection': False,
        'email_settings': False,
        'models_accessible': False,
        'overall_status': False
    }

    try:
        # Test database connection
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        health_status['database_connection'] = True
        logger.info("✓ Database connection: OK")

        # Test email settings
        if hasattr(settings, 'DEFAULT_FROM_EMAIL') and hasattr(settings, 'BEKARY_EMAIL'):
            health_status['email_settings'] = True
            logger.info("✓ Email settings: OK")
        else:
            logger.warning("✗ Email settings: Missing")

        # Test model access
        delivery_count = DeliveryDay.objects.count()
        free_box_count = FreeBoxRequest.objects.count()
        health_status['models_accessible'] = True
        logger.info(
            f"✓ Models accessible: {delivery_count} delivery days, {free_box_count} free box requests")

        # Overall status
        health_status['overall_status'] = all([
            health_status['database_connection'],
            health_status['email_settings'],
            health_status['models_accessible']
        ])

        if health_status['overall_status']:
            logger.info("✓ Overall system health: GOOD")
        else:
            logger.warning("✗ Overall system health: ISSUES DETECTED")

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

    return health_status


# ============================================================================================================================================================
@shared_task
def check_and_update_expired_orders():
    """
    Mark orders as expired only when:
    - end_date has passed
    - all deliveries (non-cancelled) are billed
    """
    today = timezone.now().date()

    active_orders = Order.objects.filter(
        is_order_active=True,
        is_order_expire=False,
        is_order_pause=False,
        status='active'
    )

    expired_count = 0

    for order in active_orders:
        if order.end_date and order.end_date < today:
            # FIXED: Get list of delivery days not cancelled and not billed
            remaining_days = DeliveryDay.objects.filter(
                week__order=order,  # Correct relationship path
                is_cancelled=False,
                is_billed=False
            )

            if not remaining_days.exists():
                # All valid deliveries are billed, expire order
                order.is_order_expire = True
                order.is_order_active = False
                order.status = 'completed'
                order.save()
                expired_count += 1
                logger.info(
                    f"🧾 Order {order.order_number} expired successfully — all delivery days completed & billed.")
                # send a email for expired order
                send_payment_confirmation.delay(order.id, order.total_amount)
                send_expired_order_email.delay(order.id)

            else:
                logger.info(
                    f"⏳ Order {order.order_number} still has {remaining_days.count()} unbilled delivery days.")

    return expired_count


@shared_task
def process_weekly_charges():
    """
    Process all weekly subscriptions that are due for payment on Monday
    Bills for the previous week's completed deliveries
    """
    today = timezone.now().date()
    logger.info(f"⏰ Running weekly charge task on {today}")

    # Find all active weekly subscriptions due for payment today
    orders = Order.objects.filter(
        subscription_type='weekly',
        status='active',
        next_billing_date=today,
        is_order_active=True,
        is_order_expire=False,
        is_order_pause=False,
        stripe_payment_method_id__isnull=False
    ).select_related('user')

    logger.info(f"🔍 Found {orders.count()} orders to process")

    results = {
        'total_orders': orders.count(),
        'successful_charges': 0,
        'failed_charges': 0,
        'total_amount': Decimal('0.00'),
        'errors': []
    }

    for order in orders:
        try:
            # For retrospective billing: bill for completed deliveries
            # Look for deliveries that have been delivered but not yet billed

            logger.info(f"🔍 DEBUG: Looking for completed deliveries to bill")

            # Find unbilled delivery days that have been delivered (status = 'delivered')
            billable_days = DeliveryDay.objects.filter(
                is_cancelled=False,
                is_billed=False,
                status='delivered',  # Only bill completed deliveries
                week__order=order,
                week__order__status='active',
                week__order__stripe_payment_method_id__isnull=False
            ).distinct().select_related('week').prefetch_related('order_items__product')

            logger.info(
                f"🔍 DEBUG: Billable days found: {billable_days.count()}")

            if not billable_days.exists():
                logger.info(
                    f"⏭️ No billable days for order {order.order_number}")
                continue

            # Calculate amount based on billable days
            total_amount = calculate_weekly_amount(
                order, billable_days, order.user)

            if total_amount <= 0:
                logger.info(f"💰 Zero amount for order {order.order_number}")
                continue

            # Process Stripe payment
            payment_success = process_stripe_charge(
                order,
                total_amount,
                f"Weekly subscription charge for order {order.order_number}"
            )

            if payment_success:
                # Update order with next billing date (next Monday)
                next_monday = today + timedelta(days=7)

                order.next_billing_date = next_monday
                order.last_payment_date = today
                order.save()

                # Get the date range for billing period
                billing_dates = billable_days.values_list(
                    'delivery_date', flat=True)
                billing_period_start = min(billing_dates)
                billing_period_end = max(billing_dates)

                # Record successful payment
                Payment.objects.create(
                    order=order,
                    amount=total_amount,
                    status='succeeded',
                    payment_type='weekly',
                    stripe_payment_intent_id=payment_success.id,
                    billing_period_start=billing_period_start,
                    billing_period_end=billing_period_end
                )
                billable_days.update(is_billed=True)

                results['successful_charges'] += 1
                results['total_amount'] += total_amount
                logger.info(
                    f"✅ Successfully charged order {order.order_number}")

                # Send payment confirmation
                send_payment_confirmation.delay(order.id, total_amount)
            else:
                results['failed_charges'] += 1
                logger.error(f"❌ Failed to charge order {order.order_number}")

        except Exception as e:
            logger.error(
                f"🔥 Error processing order {order.order_number}: {str(e)}")
            results['failed_charges'] += 1
            results['errors'].append(str(e))
            send_payment_failure.delay(order.id, str(e))

    logger.info(f"📊 Weekly charge results: {results}")
    return results


def calculate_weekly_amount(order, billable_days, user):
    """
    Calculate the weekly charge amount based on delivery days and products
    """
    total = Decimal('0.00')
    is_committed = CommitmentForSixMonths.objects.filter(
        user=user, commitment_status=True).exists()
    print(
        f"▶️Calculating total for user {user.id} with commitment status {is_committed}")

    # billable_days are DeliveryDay objects, not weeks
    for delivery_day in billable_days:
        if not delivery_day.is_cancelled:
            for item in delivery_day.order_items.all():
                item_total = item.product.price * item.quantity * delivery_day.number_of_people
                total += item_total
                print(
                    f"Added item: {item.product.name} x {item.quantity} x {delivery_day.number_of_people} people = {item_total}")

    if is_committed:
        discount_rate = Decimal('0.10')
        total *= (Decimal('1.00') - discount_rate)
        print(f"😐Total after commitment discount: {total}")

    # Add delivery fee
    delivery_fee = Decimal('1.79') * billable_days.count()
    total += delivery_fee
    print(f"✅Total after adding delivery charge: {total}")
    return total.quantize(Decimal('0.01'))


def process_stripe_charge(order, amount, description):
    """
    Process the actual Stripe charge
    """
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency='eur',
            customer=order.stripe_customer_id,
            payment_method=order.stripe_payment_method_id,
            off_session=True,
            confirm=True,
            description=description,
            metadata={
                'order_id': order.id,
                'order_number': order.order_number,
                'type': 'weekly_subscription'
            }
        )

        if payment_intent.status == 'succeeded':
            return payment_intent
        return None

    except stripe.error.CardError as e:
        logger.error(f"💳 Card error for order {order.order_number}: {str(e)}")
        return None
    except Exception as e:
        logger.error(
            f"⚡ Stripe error for order {order.order_number}: {str(e)}")
        return None


@shared_task
def send_expired_order_email(order_id):
    # Implement your email sending logic here
    try:
        order = Order.objects.get(id=order_id)
        subject = f"📦 Order #{order.order_number} Marked as Completed"
        message = (
            f"Hi {order.user.first_name},\n\n"
            f"Your order #{order.order_number} has been marked as completed.\n"
            "All deliveries have been fulfilled and payments are settled.\n\n"
            "We hope you had a great experience with us! 💫\n"
            "Let us know if there’s anything else we can help with.\n\n"
            "Stay awesome,\nYour Company Team"
        )

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [order.shipping_address.email or order.user.email])
    except Exception as e:
        logger.error(f"📧 Failed to send expired order email: {e}")


@shared_task
def send_payment_confirmation(order_id, amount):
    try:
        order = Order.objects.get(id=order_id)
        subject = f"✅ Payment Received for Order #{order.order_number}"
        message = (
            f"Hi {order.user.first_name},\n\n"
            f"We’ve successfully received your payment of ${amount:.2f} "
            f"for your order #{order.order_number}.\n"
            "Thanks for being awesome! 💜\n\n"
            "If you have any questions, just reply to this email.\n\n"
            "Cheers,\nYour Company Team"
        )

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [order.shipping_address.email or order.user.email])
    except Exception as e:
        logger.error(f"📧 Failed to send payment confirmation: {e}")


@shared_task
def send_payment_failure(order_id, error):
    try:
        order = Order.objects.get(id=order_id)
        subject = f"⚠️ Payment Failed for Order #{order.order_number}"
        message = (
            f"Hi {order.user.first_name},\n\n"
            f"Unfortunately, we couldn’t process the payment for order #{order.order_number}.\n\n"
            f"Reason: {error}\n\n"
            "Please check your payment details or contact support if the issue persists.\n\n"
            "Best,\nYour Company Team"
        )

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [order.shipping_address.email or order.user.email])
    except Exception as e:
        logger.error(f"📧 Failed to send payment failure notification: {e}")
