from .serializers import FreeBoxRequestSerializer
from .models import FreeBoxRequest
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from .models import Box
from .serializers import BoxSerializer
from django.conf import settings
from django.core.mail import send_mail
from utils.crud import DynamicModelViewSet
from .models import Box, FreeBoxRequest
from .serializers import BoxSerializer, FreeBoxRequestSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework import generics
from utils.IsAdminOrStaff import IsAdminOrHasRoleAdmin
from django.db.models import Case, When, Value, BooleanField


class BoxViewSet(DynamicModelViewSet):
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
    permission_classes = [IsAdminOrHasRoleAdmin]
    
    def create(self, request):
        # Handle product IDs in items field
        product_ids = request.data.get('items', [])
        box = Box.objects.create(name=request.data['name'])
        box.items.set(product_ids)
        serializer = self.get_serializer(box)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Save the box first
        box = serializer.save()
        
        # Update products if product_ids were provided
        if 'items' in request.data:
            box.items.set(request.data['items'])
        
        return Response(serializer.data)

    def __init__(self, *args, **kwargs):
        kwargs['model'] = Box
        kwargs['serializer_class'] = BoxSerializer
        kwargs['item_name'] = 'Box'
        super().__init__(*args, **kwargs)



class IsAdminOrCreateOnly(BasePermission):
    """
    Allow anyone to POST (create), but only admins can do other stuff.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        return request.user.is_staff or getattr(request.user, 'role', None) == 'admin'


class FreeBoxRequestViewSet(viewsets.ModelViewSet):
    queryset = FreeBoxRequest.objects.annotate(
        status_order=Case(
            When(delivery_status=False, then=Value(0)),
            When(delivery_status=True, then=Value(1)),
            default=Value(0),
            output_field=BooleanField(),
        )
    ).order_by('status_order', 'date_of_delivery')
    serializer_class = FreeBoxRequestSerializer
    permission_classes = [IsAdminOrCreateOnly]

    def list(self, request, *args, **kwargs):
        """
        Override list to add custom success metadata to the response.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = {
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Fetched FreeBoxRequests successfully.",
            "data": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to add custom success metadata to the response.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = {
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Fetched FreeBoxRequest successfully.",
            "data": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        Override update to add custom success metadata to the response.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            data = {
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "FreeBoxRequest updated successfully.",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            data = {
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Bad request. Validation failed.",
                "errors": serializer.errors
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to add custom success metadata to the response.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        data = {
            "success": True,
            "status_code": status.HTTP_204_NO_CONTENT,
            "message": "FreeBoxRequest deleted successfully."
        }
        return Response(data, status=status.HTTP_204_NO_CONTENT)


class FreeBoxRequestCreateAPIView(generics.CreateAPIView):
    queryset = FreeBoxRequest.objects.all()
    serializer_class = FreeBoxRequestSerializer
    permission_classes = [IsAuthenticated] 
    # authentication_classes = [TokenAuthentication]  

    def create(self, request, *args, **kwargs):
        """
        Override create to add custom success metadata to the response.
        """
        serializer = self.get_serializer(data=request.data)
        number_of_people = request.data.get('number_of_people')
        user = request.user
        if user.trial_status:
            return Response({
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "User already has a trial status.",
            })
        
        if number_of_people > 3:
            return Response({
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Number of people must be less than or equal to 3.",
            }) 
            

        if serializer.is_valid():
            # Check if FreeBoxRequest with the same email, phone number, or address exists
            if FreeBoxRequest.objects.filter(
                email=serializer.validated_data['email']
            ).exists() or FreeBoxRequest.objects.filter(
                phone_number=serializer.validated_data['phone_number']
            ).exists() or FreeBoxRequest.objects.filter(
                address=serializer.validated_data['address']
            ).exists():
                return Response({
                    "success": False,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "A FreeBoxRequest with this email, phone number, or address already exists.",
                }, status=status.HTTP_400_BAD_REQUEST)

            # If the validation passes, save the new FreeBoxRequest
            user = request.user
            user.trial_status = True
            user.save()
            serializer.save()

            # Send email after successful creation
            to_email = serializer.validated_data.get('email')
            name = serializer.validated_data.get('name')
            try:
                self.send_email(to_email, name)
            except Exception as e:
                return Response({
                    "success": False,
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"Failed to send email: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Success response
            data = {
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": "FreeBoxRequest created successfully.",
                "data": serializer.data
            }
            return Response(data, status=status.HTTP_201_CREATED)

        else:
            # Validation failed
            data = {
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Bad request. Validation failed.",
                "errors": serializer.errors
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def send_email(self, to_email, name):
        """
        Sends a confirmation email to the user after creating a FreeBoxRequest.
        """
        subject = "FreeBoxRequest Confirmation"
        message = f"Hello {name},\n\nYour FreeBoxRequest has been successfully created!"
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [to_email])