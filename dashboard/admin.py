from django.contrib import admin
from .models import Machine, InspectionReport, Escalation, PendingInspection  # Import the Machine model
from django.utils.html import format_html

# Register your models here.
@admin.register(Machine)

class MachineAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'engineer', 'worker', 'status', 'inspection_frequency', 'location', 'created_at')  
    search_fields = ('name', 'engineer__username', 'worker__username', 'location')  
    list_filter = ('status', 'inspection_frequency')  


class InspectionReportAdmin(admin.ModelAdmin):
    list_display = ('machine', 'worker', 'timestamp','due_date' , 'is_escalated', 'view_report')
    search_fields = ('machine__name', 'worker__username', 'timestamp', 'due_date')
    list_filter = ('is_escalated', 'timestamp', 'due_date')
    ordering = ('-timestamp',)

    # Custom method to display a clickable link to view inspection details
    def view_report(self, obj):
        return format_html('<a href="{0}">View Report</a>', obj.id)
    view_report.short_description = 'Report Details'
admin.site.register(InspectionReport, InspectionReportAdmin)


class EscalationAdmin(admin.ModelAdmin):
    list_display = ('machine', 'worker', 'engineer', 'status', 'created_at', 'resolved_at')
    search_fields = ('machine__name', 'worker__username', 'engineer__username', 'status')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)

    # Custom method to mark the escalation as resolved directly from the list view
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved', resolved_at=models.F('created_at'))
        self.message_user(request, "Escalations marked as resolved.")
    mark_as_resolved.short_description = "Mark selected escalations as resolved"

    actions = [mark_as_resolved]
admin.site.register(Escalation, EscalationAdmin)



@admin.register(PendingInspection)
class PendingInspectionAdmin(admin.ModelAdmin):
    list_display = ('machine', 'date_due', 'resolved', 'created_at')
    list_filter = ('resolved', 'date_due', 'machine')
    search_fields = ('machine__name',)  # assuming Machine has a 'name' field
    ordering = ('-date_due',)
