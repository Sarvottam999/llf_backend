from django.contrib import admin
from .models import Machine, InspectionReport, Escalation, PendingInspection  # Import the Machine model
from django.utils.html import format_html
from django import forms
from authentication.models import CustomUser  # for fetching worker by ID

# Register your models here.

class MachineAdminForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit worker choices to user_type == 'worker'
        self.fields['worker'].queryset = CustomUser.objects.filter(user_type='worker')

        # Limit engineer choices to user_type == 'engineer'
        self.fields['engineer'].queryset = CustomUser.objects.filter(user_type='engineer')
@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    form = MachineAdminForm  # 👈 Add this line
    list_display = ('id', 'name', 'engineer', 'worker', 'status', 'inspection_frequency', 'location', 'created_at')  
    search_fields = ('name', 'engineer__username', 'worker__username', 'location')  
    list_filter = ('status', 'inspection_frequency')  



class InspectionReportAdminForm(forms.ModelForm):
     

    class Meta:
        model = Escalation
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit worker choices to user_type == 'worker'
        self.fields['worker'].queryset = CustomUser.objects.filter(user_type='worker')

        # Limit engineer choices to user_type == 'engineer'
        # self.fields['engineer'].queryset = CustomUser.objects.filter(user_type='engineer')

# class InspectionReportAdmin(admin.ModelAdmin):
#     form = InspectionReportAdminForm  # 👈 Add this line
#     list_display = ('machine', 'worker', 'timestamp','due_date' , 'is_escalated', 'view_report')
#     search_fields = ('machine__name', 'worker__username', 'timestamp', 'due_date')
#     list_filter = ('is_escalated', 'timestamp', 'due_date')
#     ordering = ('-timestamp',)

#     # Custom method to display a clickable link to view inspection details
#     def view_report(self, obj):
#         return format_html('<a href="{0}">View Report</a>', obj.id)
#     view_report.short_description = 'Report Details'


class InspectionReportAdmin(admin.ModelAdmin):
    form = InspectionReportAdminForm
    list_display = (
        'machine',
        'worker',
        'timestamp',
        'due_date',
        'look',
        'feel',
        'sound',
        'is_escalated',
        'view_report',
    )
    search_fields = (
        'machine__name',
        'worker__username',
        'timestamp',
        'due_date',
        'look_comment',
        'feel_comment',
        'sound_comment',
    )
    list_filter = (
        'is_escalated',
        'timestamp',
        'due_date',
        'look',
        'feel',
        'sound',
    )
    ordering = ('-timestamp',)

    def view_report(self, obj):
        return format_html(
            '<b>Look:</b> {}<br><i>{}</i><br>'
            '<b>Feel:</b> {}<br><i>{}</i><br>'
            '<b>Sound:</b> {}<br><i>{}</i>',
            '✅' if obj.look else '❌', obj.look_comment or "No comment",
            '✅' if obj.feel else '❌', obj.feel_comment or "No comment",
            '✅' if obj.sound else '❌', obj.sound_comment or "No comment"
        )

    view_report.short_description = 'Inspection Summary'
admin.site.register(InspectionReport, InspectionReportAdmin)



class InspectionReportChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.machine.name} - {obj.worker.username} - submitted at:{obj.timestamp.date()} - due:{obj.due_date}"

class EscalationAdminForm(forms.ModelForm):
    report = InspectionReportChoiceField(
        queryset=InspectionReport.objects.all(),
        required=False
    )

    class Meta:
        model = Escalation
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit worker choices to user_type == 'worker'
        self.fields['worker'].queryset = CustomUser.objects.filter(user_type='worker')

        # Limit engineer choices to user_type == 'engineer'
        self.fields['engineer'].queryset = CustomUser.objects.filter(user_type='engineer')

class EscalationAdmin(admin.ModelAdmin):
    form = EscalationAdminForm  # 👈 Add this line
    list_display = ('machine', 'worker', 'engineer', 'status', 'report','comment' , 'created_at', 'resolved_at')
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
