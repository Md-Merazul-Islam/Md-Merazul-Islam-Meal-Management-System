from django.urls import path
from .views import TriggerProductListTask

urlpatterns = [
    path('trigger-product-list/', TriggerProductListTask.as_view(),
         name='trigger_product_list_task'),

]
