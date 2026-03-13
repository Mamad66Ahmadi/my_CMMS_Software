from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, PermissionsMixin)
from django.utils.translation import gettext_lazy as _


# ----------------------    Custom User Manager    ----------------------------------
class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        """
        Creates and saves a User with the given username and password.
        """
        if not username:
            raise ValueError(_('The Username must be set'))
        
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db) # using=self._db?
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        extra_fields.setdefault('is_active',True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(username, password, **extra_fields)



# ----------------------    Custom User Model    ----------------------------------
class User(AbstractBaseUser,PermissionsMixin):
    username = models.CharField(max_length=50, unique=True, primary_key=True,)
    personnel_number = models.IntegerField()
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    class Role(models.TextChoices):
        TECHNITION = 'technician', 'Technician'
        ENGINEER = 'engineer', 'Engineer'
        SUPERVISOR = 'supervisor', 'Supervisor'     

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TECHNITION)


    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey('self', on_delete=models.PROTECT,null=True,blank=True,related_name='users_created')
    modified_by = models.ForeignKey('self', on_delete=models.PROTECT,null=True,blank=True,related_name='users_modified')

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['personnel_number', 'first_name', 'last_name']


    def __str__(self):
        return self.username
    
    class Meta:
        ordering = ['username']


# ----------------------    Department Model    ----------------------------------

class Department(models.Model):
    """
    Represents a department or unit within the organization.
    """
    department_code = models.CharField(max_length=10, unique=True, primary_key=True, verbose_name="Department Code")
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Department Name")
    
    description = models.TextField(blank=True, null=True)

    # Audit Fields
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='departments_created')

    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='departments_modified')
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.department_code})"

    class Meta:
        ordering = ['department_code']