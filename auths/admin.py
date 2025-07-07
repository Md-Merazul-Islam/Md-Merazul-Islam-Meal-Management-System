from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'id', 'username', 'role', 'is_staff',
                    'is_active',  'trial_status', 'city', 'postal_code', 'phone_number')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'username')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name',
         'address', 'city', 'postal_code', 'phone_number', 'photo')}),
        ('Permissions', {'fields': ('role', 'is_active',
         'is_staff', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_active', 'is_staff')
        }),
    )
    filter_horizontal = ('groups', 'user_permissions')


class UserProfileAdmin(admin.ModelAdmin):
    model = UserProfile
    list_display = ('user', 'otp', 'otp_created_at', 'is_otp_expired')
    search_fields = ('user__email',)
    list_filter = ('otp_created_at',)
    ordering = ('user',)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
