from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, password=None, worker_id=None, **extra_fields):
        if not email and not worker_id:
            raise ValueError("Either email or worker_id is required")

        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, worker_id=worker_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "admin")

        return self.create_user(email=email, password=password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ("admin", "Admin"),
        ("engineer", "Engineer"),
        ("worker", "Worker"),
    )

    email = models.EmailField(unique=True, null=True, blank=True)  # Email is now optional
    worker_id = models.CharField(max_length=50, unique=True, null=True, blank=True)  # Unique Worker ID
    created_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_workers")  # Tracks creator

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default="worker")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Set worker_id as the primary authentication field when email is missing
    USERNAME_FIELD = "email"  
    REQUIRED_FIELDS = ["user_type"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email if self.email else self.worker_id
