
from .views import DeliveryScheduleViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderAcceptanceView, OrderDetailView, OrderCreateAPIView, PauseOrderRequestView, ResumeOrderView, DeleteOrderDataView, UpdateOrderDataStatusView, GroupOrdersByDeliveryDate, PaymentConfirmAPIView, CreatePaymentIntentView, PaymentConfirmByPayPalAPIView, CreatePaymentByPayPalIntentView, DashboardOverview, send_order_report, AreaRevenueView

from .views import CreateStripPaymentIntentView, PaymentStripeConfirmAPIView, PaymentConfirmByPayPalAPIView, CreatePaymentPayPalIntentView, CombinedDeliveryListView
from .views import CreateWeeklySubscriptionView, stripe_webhook

from .views import SetupCardForSubscriptionView, ConfirmCardAndCreateSubscriptionView, ManageSubscriptionView, SubscriptionDetailsView
from .views import DeliverySchedulesAPIView
from . import views

from .views import (
    RequestDeliveryActionView,
    AdminApproveDeliveryActionView,
    SubscriptionActivationView,
    ListOfRequestsView
)


router = DefaultRouter()
router.register(r'orders', OrderViewSet)
router.register(r'delivery-list', DeliveryScheduleViewSet, basename='delivery')

urlpatterns = [
    path('', include(router.urls)),
    path('create-order/', OrderCreateAPIView.as_view(), name='create-order'),
    path('orders/<int:order_id>/accept/',
         OrderAcceptanceView.as_view(), name='order-acceptance'),
    path('orders/<int:order_id>/status/',
         OrderDetailView.as_view(), name='order-acceptance'),

    path('orders/<int:order_id>/pause/',
         PauseOrderRequestView.as_view(), name='pause-order'),
    path('orders/<int:order_id>/resume/',
         ResumeOrderView.as_view(), name='resume-order'),

    # delete order item
    path('orders/items/delete/<str:order_data_id>/',
         DeleteOrderDataView.as_view(), name='delete-order-items-by-date'),

    # order data
    path('order-data/<int:order_data_id>/update-status/',
         UpdateOrderDataStatusView.as_view(), name='update-order-data-status'),
    path('orders/upcoming/list/', GroupOrdersByDeliveryDate.as_view(),
         name='orders-by-delivery-date'),


    # payment CreatePaymentIntentView
    path('payment/create-intent/', CreatePaymentIntentView.as_view(),
         name='create-payment-intent'),
    path('payment/confirm/', PaymentConfirmAPIView.as_view(),
         name='confirm-payment'),

    # paypal payment
    path('payment/paypal/create-intents/', CreatePaymentByPayPalIntentView.as_view(),
         name='create-paypal-payment-intent'),
    path('payment/paypal/confirms/', PaymentConfirmByPayPalAPIView.as_view(),
         name='confirm-paypal-payment'),

    # dashboard overview
    path('dashboard/overview/', DashboardOverview.as_view(),
         name='dashboard-overview'),

    path('send-order-report/', send_order_report, name='send_order_report'),


    # payment  stripe v2
    path('payment/stripe/create-intent/', CreateStripPaymentIntentView.as_view(),
         name='create-stripe-payment-intent'),
    path('payment/stripe/confirm/', PaymentStripeConfirmAPIView.as_view(),
         name='confirm-stripe-payment'),

    # payment paypal v2
    path('payment/paypal/create-intent/', CreatePaymentPayPalIntentView.as_view(),
         name='create-paypal-payment-intent'),
    path('payment/paypal/confirm/', PaymentConfirmByPayPalAPIView.as_view(),
         name='confirm-paypal-payment'),

    # combined delivery list
    path('area-revenue/', AreaRevenueView.as_view(), name='area-revenue'),
    path('combined-delivery-list/', CombinedDeliveryListView.as_view(),
         name='combined-delivery-list'),


    # stripe webhook
    path('stripe-webhook/', stripe_webhook, name='stripe-webhook'),
    # weekly subscription
    path('weekly-subscription/', CreateWeeklySubscriptionView.as_view(),
         name='weekly-subscription'),


    #####
    path('setup-card/', SetupCardForSubscriptionView.as_view(), name='setup_card'),
    path('confirm-subscription/', ConfirmCardAndCreateSubscriptionView.as_view(),
         name='confirm_subscription'),

    # Subscription management - note the <int:order_id> parameter
    path('manage-subscription/<int:order_id>/',
         ManageSubscriptionView.as_view(), name='manage_subscription'),

    # Optional: Get subscription details
    path('subscription-details/<int:order_id>/',
         SubscriptionDetailsView.as_view(), name='subscription_details'),
    # Delivery schedules
    path('delivery-schedules/', DeliverySchedulesAPIView.as_view(),
         name='delivery_schedules'),
    
    # Delivery Action & Approval & Subscription
     path('request-delivery-action/', RequestDeliveryActionView.as_view(),name='request-delivery-action'),
    path('list-delivery-requests/', ListOfRequestsView.as_view(),name='list-delivery-requests'),
    path('admin/approve-delivery-action/<int:request_id>/', AdminApproveDeliveryActionView.as_view(),    name='admin-approve-delivery-action'),
    path('subscription/toggle/<int:order_id>/', SubscriptionActivationView.as_view(), name='toggle-subscription'),

]
