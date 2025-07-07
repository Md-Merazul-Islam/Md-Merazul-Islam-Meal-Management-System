from rest_framework import serializers
from .models import NewsletterSubscription

class UnsubscribeNewsletterSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            subscription = NewsletterSubscription.objects.get(email=value)
            if not subscription.is_subscribed:
                raise serializers.ValidationError("You are already unsubscribed.")
        except NewsletterSubscription.DoesNotExist:
            raise serializers.ValidationError("This email is not subscribed.")
        return value


class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscription
        fields = ['id', 'email', 'subscribed_at', 'is_subscribed']
        read_only_fields = ['subscribed_at']