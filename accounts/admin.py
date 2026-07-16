from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, Qualification, User, UserQualification


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = (
        "username",
        "first_name",
        "last_name",
        "personnel_number",
        "department",
        "role",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_staff", "is_active", "department")
    search_fields = ("username", "first_name", "last_name", "personnel_number")
    ordering = ("personnel_number",)
    readonly_fields = ("created_date", "modified_date", "last_login")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "personnel_number", "department", "role")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important Dates", {"fields": ("last_login",)}),
        (
            "Audit Information",
            {"fields": ("created_date", "created_by", "modified_date", "modified_by"), "classes": ("collapse",)},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "personnel_number",
                    "first_name",
                    "last_name",
                    "department",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


admin.site.register(User, CustomUserAdmin)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("department_code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "department_code")
    ordering = ("department_code",)
    readonly_fields = ("created_date", "modified_date")

    fieldsets = (
        (None, {"fields": ("department_code", "name", "description")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {"fields": ("created_date", "created_by", "modified_date", "modified_by"), "classes": ("collapse",)},
        ),
    )


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("code",)
    readonly_fields = ("created_date", "modified_date")

    fieldsets = (
        (None, {"fields": ("code", "name", "description")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {"fields": ("created_date", "created_by", "modified_date", "modified_by"), "classes": ("collapse",)},
        ),
    )


@admin.register(UserQualification)
class UserQualificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "qualification",
        "granted_date",
        "expiry_date",
        "is_active",
    )
    list_filter = ("qualification", "is_active", "granted_date", "expiry_date")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "qualification__code",
        "qualification__name",
        "note",
    )
    ordering = ("user__username", "qualification__code")
    autocomplete_fields = ("user", "qualification", "granted_by", "created_by", "modified_by")
    readonly_fields = ("created_date", "modified_date")

    fieldsets = (
        (None, {"fields": ("user", "qualification", "granted_by")}),
        ("Dates", {"fields": ("granted_date", "expiry_date")}),
        ("Details", {"fields": ("note", "is_active")}),
        (
            "Audit Information",
            {"fields": ("created_date", "created_by", "modified_date", "modified_by"), "classes": ("collapse",)},
        ),
    )
