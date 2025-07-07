
from utils.pagination import CustomPagination
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import viewsets
from .serializers import CancelDeliverySerializer
from .models import CancelDelivery
from utils.success_failer import success_response, failure_response


from rest_framework.permissions import IsAuthenticated
from utils.IsAdminOrStaff import IsAdminOrStaff


class CancelDeliveryView(generics.ListCreateAPIView):
    queryset = CancelDelivery.objects.all()
    serializer_class = CancelDeliverySerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        if CancelDelivery.objects.filter(user=user, delivery_day=request.data['delivery_day']).exists():
            return failure_response({"message": "You have already requested for this delivery day."}, "You have already requested for this delivery day")
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return success_response("CancelDelivery created successfully", serializer.data)


class CancelDeliveryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CancelDelivery.objects.all()
    serializer_class = CancelDeliverySerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response("CancelDelivery updated successfully", serializer.data)


class ApproveCancelRequest(APIView):
    def post(self, request, pk):
        try:
            cancel_delivery = CancelDelivery.objects.get(id=pk)

            delivery = cancel_delivery.delivery_day
            delivery.is_cancelled = True
            delivery.status = 'cancelled'
            delivery.save()

            cancel_delivery.request_status = 'approved'
            cancel_delivery.save()
            serializer = CancelDeliverySerializer(cancel_delivery)
            return success_response("CancelDelivery request approved successfully", serializer.data)
        except Exception as e:
            return failure_response("Failed to approve CancelDelivery request", str(e))


class RejectCancelRequest(APIView):
    def post(self, request, pk):
        try:
            cancel_delivery = CancelDelivery.objects.get(id=pk)
            cancel_delivery.request_status = 'rejected'
            cancel_delivery.save()
            serializer = CancelDeliverySerializer(cancel_delivery)
            return success_response("CancelDelivery request rejected successfully", serializer.data)
        except Exception as e:
            return failure_response("Failed to reject CancelDelivery request", str(e))

class ReadOnlyCancelDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CancelDelivery.objects.all()
    serializer_class = CancelDeliverySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.is_staff or getattr(self.request.user, 'role', None) == 'admin':
            return CancelDelivery.objects.all().order_by('-created_at')
        else:
            user = self.request.user
            return CancelDelivery.objects.filter(user=user).order_by('-created_at')



