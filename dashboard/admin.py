from django.contrib import admin
from .models import Machine  # Import the Machine model

# Register your models here.
@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('name', 'engineer', 'worker', 'status', 'inspection_frequency', 'location', 'created_at')  
    search_fields = ('name', 'engineer__username', 'worker__username', 'location')  
    list_filter = ('status', 'inspection_frequency')  
