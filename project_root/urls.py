from django.contrib import admin
from django.urls import path, include, re_path

from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from django.http import HttpResponse
from django.urls import re_path


def favicon(request):
    return HttpResponse(status=204)


def home(request):
    return JsonResponse({"message": "Welcome to the Gepixelt  REST API!"})


urlpatterns = [
    path("", home),
    re_path(r'^favicon.ico$', favicon),
    path('admin/', admin.site.urls),
    path('api/v1/', include([
        path('auth/', include('auths.urls')),
        path('products/', include('products.urls')),
        path('contacts/', include('contacts.urls')),
        path('auto-email/', include('autoemail.urls')),
        path('areas/', include('areas.urls')),
        path('newsletter/', include('newsletter.urls')),
        path('subscriptions/', include('subscriptions.urls')),
        path('order-app/', include('order_app.urls')),
        path('week-order/', include('weekly_order_manage.urls')),
        path('week-order-admin/', include('week_order_admin.urls')),
        

    ])),
]
