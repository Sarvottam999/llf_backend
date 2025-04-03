from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('id', 'date_joined', 'email', 'worker_id', 'user_type', 'created_by', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password', 'worker_id')}),
        ('Permissions', {'fields': ('user_type', 'is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'worker_id', 'password1', 'password2', 'user_type', 'is_staff', 'is_active')
        }),
    )
    search_fields = ('email', 'worker_id')
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)
