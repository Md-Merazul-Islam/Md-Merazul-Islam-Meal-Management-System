from order_app.models import Order
from datetime import timedelta
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

from collections import defaultdict
from django.template.loader import render_to_string


@shared_task
def send_order_confirmation_email(customer_name, customer_email, created_orders, total_amount):
    order_details = "\n".join([
        f"Day: {order['order_delivery_date']}, People: {order['number_of_people']}, Total: {order['total_order_price']}\n"
        + "\n".join([f"{item['product']}: {item['quantity']}" for item in order['order_items']])
        for order in created_orders
    ])

    # Send the email
    subject = "Order Confirmation"
    message = f"Dear {customer_name},\n\nYour orders have been successfully created. Here are the details:\n\n{order_details}\n\nTotal Amount: {total_amount}\n\nThank you for your order!"
    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[customer_email],
    )

    print(f"Confirmation email sent to {customer_email}")
    return "Email sent successfully"


@shared_task
def send_order_creation_email(order_id):
    order = Order.objects.get(id=order_id)

    # Prepare HTML email content
    subject = 'Order Confirmation'

    message = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                color: #333;
                padding: 20px;
            }}
            .container {{
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                padding: 30px;
                max-width: 600px;
                margin: 0 auto;
            }}
            h2 {{
                color: #007C74;
                text-align: center;
            }}
            .order-info {{
                margin-top: 20px;
                padding: 20px;
                border-top: 2px solid #f1f1f1;
            }}
            .order-info p {{
                font-size: 16px;
                line-height: 1.5;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 14px;
                color: #888;
            }}
            .button {{
                background-color: #007C74;
                color: #ffffff;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
                margin-top: 20px;
                display: block;
                width: 200px;
                margin-left: auto;
                margin-right: auto;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Order Confirmation</h2>
            <p>Dear {order.user.username},</p>
            <p>We are excited to inform you that your order has been successfully created! Below are the details:</p>

            <div class="order-info">
                <p><strong>Order Number:</strong> {order.order_number}</p>
                <p><strong>Subscription Type:</strong> {order.get_subscription_type_display()}</p>
                <p><strong>Status:</strong> {order.get_status_display()}</p>
                <p><strong>Total Amount:</strong> ${order.total_amount}</p>
                <p><strong>Shipping Address:</strong> {order.shipping_address}</p>
                <p><strong>Phone Number:</strong> {order.phone_number}</p>
                <p><strong>Postal Code:</strong> {order.postal_code}</p>
                <p><strong>Order Created On:</strong> {order.order_created_date.strftime('%B %d, %Y')}</p>
            </div>

            <p>Your order is currently awaiting approval. Please keep an eye on your account for updates.</p>

            <a href="#" class="button">View Your Order</a>

            <div class="footer">
                <p>Thank you for shopping with us!<br>Best regards,<br>Your Company Name</p>
            </div>
        </div>
    </body>
    </html>
    """

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [order.user.email]

    # Send the email
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        html_message=message
    )


@shared_task
def resume_paused_orders():
    paused_orders = Order.objects.filter(status='paused')

    for order in paused_orders:
        pause_request = order.pause_request
        if pause_request and timezone.now() >= pause_request.pause_end_date:
            order.status = 'processing'  # Resume the order
            order.save()


@shared_task
def send_payment_confirmation_email(to_email, customer_name, amount, transaction_id):
    subject = 'Zahlungsbestätigung'

    # Render the HTML template with the dynamic context
    message = render_to_string('payment_confirmation_email.html', {
        'customer_name': customer_name,
        'amount': amount,
        'transaction_id': transaction_id
    })

    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(subject, message, from_email, [
                  to_email], html_message=message)
        print(f"Payment confirmation email sent to {to_email}")
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
