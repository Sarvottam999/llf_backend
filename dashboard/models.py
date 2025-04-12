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
