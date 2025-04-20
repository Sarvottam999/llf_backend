from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('id', 'username', 'email', 'worker_id', 'user_type', 'created_by', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_active')
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'worker_id', 'password')}),
        ('Permissions', {'fields': ('user_type', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Metadata', {'fields': ('created_by',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'worker_id', 'password1', 'password2', 'user_type', 'is_staff', 'is_active'),
        }),
    )

    search_fields = ('username', 'email', 'worker_id')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
