
from rest_framework import status, views, viewsets
from rest_framework.response import Response
from .models import NewsletterSubscription
from .serializers import NewsletterSubscriptionSerializer, UnsubscribeNewsletterSerializer
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from utils.success_failer import success_response, failure_response
from rest_framework.decorators import action
from utils.pagination import CustomPagination

class SubscribeNewsletterView(views.APIView):
    """
    API endpoint to allow users to subscribe to the newsletter.
    """

    def post(self, request):
        serializer = NewsletterSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if NewsletterSubscription.objects.filter(email=email).exists():
                return failure_response("You are already subscribed.", status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return success_response("Subscription successful.", {email}, status=status.HTTP_201_CREATED)
        return failure_response("Invalid data.", serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnsubscribeNewsletterView(views.APIView):
    """API endpoint to allow users to unsubscribe from the newsletter.
    """

    def post(self, request):
        serializer = UnsubscribeNewsletterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                subscription = NewsletterSubscription.objects.get(email=email)
                subscription.is_subscribed = False  
                subscription.save()
                return success_response("You have successfully unsubscribed.", status=status.HTTP_200_OK)
            except NewsletterSubscription.DoesNotExist:
                return failure_response("This email is not subscribed.", status=status.HTTP_404_NOT_FOUND)
        return failure_response("Invalid data.", serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendNewsletterView(views.APIView):
    """
    API endpoint to send a newsletter to all subscribed users.
    """

    def post(self, request):
        
        subject = request.data.get('subject')
        content = request.data.get('content')

        if not subject or not content:
            return failure_response("Subject and content are required.", status=status.HTTP_400_BAD_REQUEST)

        
        subscribers = NewsletterSubscription.objects.filter(is_subscribed=True)
        recipient_list = [subscriber.email for subscriber in subscribers]

        if not recipient_list:
            return failure_response("No subscribers to send the newsletter.", status=status.HTTP_400_BAD_REQUEST)

        
        html_message = render_to_string('email_template.html', {
            'subject': subject,
            'content': content,
        })

        
        send_mail(
            subject,
            content,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            html_message=html_message,  
            fail_silently=False,
        )

        return success_response("Newsletter sent successfully.", status=status.HTTP_200_OK)


class NewsletterSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = NewsletterSubscription.objects.all()
    serializer_class = NewsletterSubscriptionSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        """
        List all newsletter subscriptions with pagination.
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)  # This automatically handles pagination

        if page is not None:
            # Return paginated data
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # If no pagination (e.g., no page size limit), return all data
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "statusCode": status.HTTP_200_OK,
            "message": "Subscriptions fetched successfully.",
            "data": serializer.data
        })

    @action(detail=True, methods=['post'])
    def unsubscribe(self, request, pk=None):
        """
        Unsubscribe a user from the newsletter.
        """
        try:
            subscription = self.get_object()
            subscription.is_subscribed = False
            subscription.save()
            return success_response(f"User with email {subscription.email} has been unsubscribed.", status=status.HTTP_200_OK)
        except NewsletterSubscription.DoesNotExist:
            return failure_response("User not found.", status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """
        Delete a user from the newsletter subscriptions.
        """
        try:
            subscription = self.get_object()
            subscription.delete()
            return success_response(f"User with email {subscription.email} has been deleted.", status=status.HTTP_204_NO_CONTENT)
        except NewsletterSubscription.DoesNotExist:
            return failure_response("User not found.", status=status.HTTP_404_NOT_FOUND)