from django.contrib import admin
from .models import Area, PostalCode, DeliveryManArea, Review

# # Try to register Area, but if it's already registered, do nothing
# try:
#     admin.site.register(Area)
# except admin.sites.AlreadyRegistered:
#     pass

# PostalCode model admin
class PostalCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'area')
    search_fields = ('code',)

admin.site.register(PostalCode, PostalCodeAdmin)

# DeliveryManArea model admin
class DeliveryManAreaAdmin(admin.ModelAdmin):
    list_display = ('delivery_man', 'area', 'create_at', 'average_rating')
    search_fields = ('delivery_man__username', 'area__name')
    list_filter = ('area',)

admin.site.register(DeliveryManArea, DeliveryManAreaAdmin)

# Review model admin
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('delivery_man', 'user', 'rating', 'review_text', 'created_at')
    search_fields = ('delivery_man__delivery_man__username', 'user__username')
    list_filter = ('rating', 'created_at')

admin.site.register(Review, ReviewAdmin)
