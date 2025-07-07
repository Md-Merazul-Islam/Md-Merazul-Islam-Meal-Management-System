# urls.py
from django.urls import path
from .views import SubscribeNewsletterView, SendNewsletterView, UnsubscribeNewsletterView
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NewsletterSubscriptionViewSet

router = DefaultRouter()
router.register(r'subscriptions-list', NewsletterSubscriptionViewSet,basename='newsletter_subscription')

urlpatterns = [
    path('', include(router.urls)),
    path('subscribe/', SubscribeNewsletterView.as_view(),
         name='subscribe-newsletter'),
    path('send-newsletter/', SendNewsletterView.as_view(), name='send-newsletter'),
    path('unsubscribe/', UnsubscribeNewsletterView.as_view(),
         name='unsubscribe-newsletter'),
]
