from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User,Department
# Register your models here.

# ----------------------    User Admin    ----------------------------------
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'first_name', 'last_name', 'personnel_number', 'department', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'department')
    search_fields = ('username', 'first_name', 'last_name', 'personnel_number')
    ordering = ('personnel_number',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'personnel_number', 'department', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login',)}),
        ('Audit Information', {'fields': ('created_date', 'created_by', 'modified_date', 'modified_by'), 'classes': ('collapse',)}),
    )


    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'personnel_number', 'first_name', 'last_name', 'department', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('created_date', 'modified_date', 'last_login')


admin.site.register(User, CustomUserAdmin)


# ----------------------    Department Admin    ----------------------------------
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_code', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'department_code')
    ordering = ('department_code',)
    
    fieldsets = (
        (None, {'fields': ('department_code', 'name', 'description')}),
        ('Status', {'fields': ('is_active',)}),
        ('Audit Information', {'fields': ('created_date', 'created_by', 'modified_date', 'modified_by'), 'classes': ('collapse',)}),
    )
    
    readonly_fields = ('created_date', 'modified_date')