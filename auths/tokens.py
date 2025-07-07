from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six
from django.utils.timezone import now
from datetime import timedelta

class EmailActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.is_active)

    def is_token_expired(self, timestamp):
        token_time = now() - timedelta(seconds=timestamp)
        expiration_time = timedelta(hours=6)
        return token_time > expiration_time

email_activation_token = EmailActivationTokenGenerator()
