from django.db import models
from authentication.models import CustomUser
from django.utils.translation import gettext_lazy as _

class Machine(models.Model):
    class InspectionFrequency(models.TextChoices):
        DAILY = "daily", _("Daily")
        WEEKLY = "weekly", _("Weekly")
        MONTHLY = "monthly", _("Monthly")

    name = models.CharField(max_length=255)
    engineer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="machines")
    worker = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_machines")
    status = models.CharField(max_length=20, choices=[("normal", "Normal"), ("abnormal", "Abnormal")], default="normal")
    inspection_frequency = models.CharField(
        max_length=10, choices=InspectionFrequency.choices, default=InspectionFrequency.MONTHLY
    )
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


 
class InspectionReport(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()  # When the inspection was expected

    # Boolean checkboxes for inspection outcome
    look = models.BooleanField(default=True)
    feel = models.BooleanField(default=True)
    sound = models.BooleanField(default=True)

    # Additional comment fields
    look_comment = models.TextField(blank=True, null=True)
    feel_comment = models.TextField(blank=True, null=True)
    sound_comment = models.TextField(blank=True, null=True)

    is_escalated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.machine.name} - {self.worker.username} - {self.due_date}"




class PendingInspection(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    date_due = models.DateField()  # The date it was due
    resolved = models.BooleanField(default=False)  # Updated when inspection is done
    created_at = models.DateTimeField(auto_now_add=True)

class Escalation(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    engineer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_escalations')
    report = models.ForeignKey(InspectionReport, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.TextField()
    status = models.CharField(max_length=20, choices=(('pending', 'Pending'), ('resolved', 'Resolved')), default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
