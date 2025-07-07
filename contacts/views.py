from rest_framework import  generics, viewsets, status, pagination
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
import requests
from .models import Contact
from .serializers import ContactSerializer

logger = logging.getLogger(__name__)


class CustomPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100



def success_response(message, data=None, status_code=status.HTTP_200_OK):
    return Response({
        "success": True,
        "statusCode": status_code,
        "message": message,
        "data": data
    }, status=status_code)


def failure_response(message, error=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({
        "success": False,
        "statusCode": status_code,
        "message": message,
        "error": error
    }, status=status_code)


class ContactCreateView(generics.CreateAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

    def create(self, request, *args, **kwargs):
        # Serialize and validate the incoming data
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                email = serializer.validated_data.get('email')
                name = serializer.validated_data.get('name', '')
                message = serializer.validated_data.get('message', '')

                # Validate if the name is provided
                if not name:
                    return Response({"success": False, "message": "Name is required"}, status=status.HTTP_400_BAD_REQUEST)

                # Validate if the email is provided
                if not email:
                    return Response({"success": False, "message": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

                # Limit the number of messages per email in the last 24 hours
                time_threshold = timezone.now() - timedelta(days=1)
                message_count = Contact.objects.filter(email=email, created_at__gte=time_threshold).count()

                if message_count >= 5:
                    return Response({
                        "success": False,
                        "message": "Too many requests from this email in the last 24 hours"
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)

                # Save contact to DB
                contact = serializer.save()

                # Build email body for the admin
                email_body = f"""
                        📄 New Contract Submitted:
                        Name: {name} 
                        Email: {email}
                        Message: {message}
                        Created At: {contact.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                        """

                # Send email to admin
                try:
                    send_mail(
                        subject="New Contract Submission",
                        message=email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[settings.ADMIN_EMAIL],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email to admin: {e}")

                # Send confirmation email to the user
                try:
                    send_mail(
                        subject="Your Contract Submission",
                        message=f"Dear {name},\n\nThank you for your contract submission. We have received your message and will respond shortly.\n\nMessage:\n{message}\n\nBest regards,\nBWEAL",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email to user {email}: {e}")

                return Response({
                    "success": True,
                    "message": "Contract successfully submitted!",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Contract submission failed: {str(e)}")
                return Response({
                    "success": False,
                    "message": "Failed to create contract",
                    "error": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": False,
            "message": "Invalid contract data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class ContactViewSetList(viewsets.ModelViewSet):
    queryset = Contact.objects.all().order_by('-id')
    serializer_class = ContactSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("All Contacts fetched successfully", serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response("Contact details fetched successfully", serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response("Contact created successfully", serializer.data, status.HTTP_201_CREATED)
        return failure_response("Contact creation failed", serializer.errors)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response("Contact updated successfully", serializer.data)
        return failure_response("Contact update failed", serializer.errors)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response("Contact deleted successfully", None, status.HTTP_200_OK)



class RecaptchaVerifyAPIView(APIView):
    def post(self, request):
        token = request.data.get('recaptcha_token')

        if not token:
            return Response({"success": False, "message": "Missing reCAPTCHA token."}, status=400)

        url = "https://www.google.com/recaptcha/api/siteverify"
        payload = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': token
        }

        res = requests.post(url, data=payload)
        result = res.json()

        if result.get('success'):
            return success_response("CAPTCHA verified.", status_code=status.HTTP_200_OK)
        else:
            return failure_response("CAPTCHA verification failed.", {}, status.HTTP_400_BAD_REQUEST)
