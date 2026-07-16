# accounts/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

# ----------------------    Custom User Manager    ----------------------------------
class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError(_("The Username must be set"))

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(username, password, **extra_fields)

# ----------------- Audit history model ------------------------
class AuditHistoryModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_modified",
    )
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True


# ----------------------    Department Model    ----------------------------------
class Department(AuditHistoryModel):
    """
    Represents a department or unit within the organization.
    """
    department_code = models.CharField(max_length=10,unique=True, primary_key=True, verbose_name="Department Code",)

    name = models.CharField(max_length=100,unique=True,verbose_name="Department Name",)

    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.department_code})"

    class Meta:
        ordering = ["department_code"]

# ----------------------    Custom User Model    ----------------------------------

class User(AuditHistoryModel, AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True, primary_key=True)
    personnel_number = models.IntegerField(unique=True)
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    department = models.ForeignKey("Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="users",)
    is_staff = models.BooleanField(default=False)

    class Role(models.TextChoices):
        TECHNICIAN = "technician", "Technician"
        ENGINEER = "engineer", "Engineer"
        SUPERVISOR = "supervisor", "Supervisor"

    role = models.CharField(max_length=20,choices=Role.choices,default=Role.TECHNICIAN,)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["personnel_number", "first_name", "last_name"]

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.username

    class Meta:
        ordering = ["username"]



# ----------------- Qualifications ------------------
class Qualification(AuditHistoryModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        ordering = ["code"]

class UserQualification(AuditHistoryModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qualifications",)
    qualification = models.ForeignKey("Qualification", on_delete=models.CASCADE, related_name="user_qualifications",)

    granted_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_qualifications",
    )

    class Meta:
        ordering = ["user__username", "qualification__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "qualification"],
                name="unique_user_qualification",
            )
        ]
        indexes = [
            models.Index(fields=["qualification", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["expiry_date"]),
        ]

    def clean(self):
        super().clean()
        if self.expiry_date and self.granted_date and self.expiry_date < self.granted_date:
            raise ValidationError("Expiry date cannot be before granted date.")

    def __str__(self):
        return f"{self.user} - {self.qualification.code}"
