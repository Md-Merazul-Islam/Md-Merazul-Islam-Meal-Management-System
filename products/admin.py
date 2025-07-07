from django.contrib import admin
from .models import Category, Product

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('slug',)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','main_price', 'price', 'category')
    search_fields = ['name', 'description']
    list_filter = ('category',)
    list_editable = ('category',)

# Register models with the admin site
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
