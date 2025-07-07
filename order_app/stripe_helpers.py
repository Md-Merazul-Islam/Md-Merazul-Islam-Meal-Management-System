import stripe
from django.conf import settings
from .models import StripeCustomer   # adjust import if utils is elsewhere

def get_or_create_stripe_customer(user):
    """
    Return the Stripe customer ID for this user,
    creating a new Stripe customer + local StripeCustomer row if missing.
    """
    if hasattr(user, "stripe_customer"):
        return user.stripe_customer.stripe_customer_id

    customer = stripe.Customer.create(email=user.email)
    StripeCustomer.objects.create(
        user=user,
        stripe_customer_id=customer.id,
    )
    return customer.id
