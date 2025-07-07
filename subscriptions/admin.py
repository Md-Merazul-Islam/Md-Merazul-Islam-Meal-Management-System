from django.contrib import admin
from .models import Box, FreeBoxRequest


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ( 'id','name',)
    search_fields = ('name',)
    list_filter = ('name',)
    ordering = ('name',)


@admin.register(FreeBoxRequest)
class FreeBoxRequestAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'phone_number', 'email', 'box', 'number_of_people', 
        'date_of_delivery', 'delivery_status', 'area_name', 'postal_code'
    )
    search_fields = ('name', 'phone_number', 'email', 'postal_code', 'address')
    list_filter = ('delivery_status', 'date_of_delivery', 'area_name')
    ordering = ('-date_of_delivery',)
    readonly_fields = ('area_name',) 

    fieldsets = (
        (None, {
            'fields': ('name', 'phone_number', 'email', 'message')
        }),
        ('Delivery Details', {
            'fields': ('box', 'number_of_people', 'date_of_delivery', 'postal_code', 'area_name', 'address', 'delivery_status')
        }),
    )
