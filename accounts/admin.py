from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Department,
    Qualification,
    User,
    UserFilterFavorite,
    UserQualification,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("department_code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "department_code")
    ordering = ("department_code",)
    readonly_fields = ("created_date", "modified_date", "created_by", "modified_by")
    # removed autocomplete_fields for created_by, modified_by

    fieldsets = (
        (None, {"fields": ("department_code", "name", "description")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {
                "fields": ("created_date", "created_by", "modified_date", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("code",)
    readonly_fields = ("created_date", "modified_date", "created_by", "modified_by")
    # removed autocomplete_fields for created_by, modified_by

    fieldsets = (
        (None, {"fields": ("code", "name", "description")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {
                "fields": ("created_date", "created_by", "modified_date", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = (
        "id", "username", "first_name", "last_name",
        "personnel_number", "department", "role", "is_staff", "is_active",
    )
    list_filter = ("role", "is_staff", "is_active", "department")
    search_fields = ("username", "first_name", "last_name", "=personnel_number")
    ordering = ("personnel_number",)
    readonly_fields = ("id", "created_date", "modified_date", "last_login", "created_by", "modified_by")
    autocomplete_fields = ("department",)  # removed created_by, modified_by
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("id", "username", "password")}),
        ("Personal Information", {"fields": ("first_name", "last_name", "personnel_number", "department", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important Dates", {"fields": ("last_login",)}),
        (
            "Audit Information",
            {
                "fields": ("created_date", "created_by", "modified_date", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": (
            "username", "personnel_number", "first_name", "last_name",
            "department", "role", "password1", "password2",
            "is_staff", "is_superuser", "is_active",
        )}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserQualification)
class UserQualificationAdmin(admin.ModelAdmin):
    list_display = (
        "user", "qualification", "granted_by",
        "granted_date", "expiry_date", "is_active",
    )
    list_filter = ("qualification", "is_active", "granted_date", "expiry_date")
    search_fields = (
        "user__username", "user__first_name", "user__last_name",
        "qualification__code", "qualification__name", "note",
    )
    ordering = ("user__username", "qualification__code")
    autocomplete_fields = ("user", "qualification", "granted_by")  # removed created_by, modified_by
    readonly_fields = ("created_date", "modified_date", "created_by", "modified_by")

    fieldsets = (
        (None, {"fields": ("user", "qualification", "granted_by")}),
        ("Dates", {"fields": ("granted_date", "expiry_date")}),
        ("Details", {"fields": ("note", "is_active")}),
        (
            "Audit Information",
            {
                "fields": (
                    "created_date", "created_by",
                    "modified_date", "modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserFilterFavorite)
class UserFilterFavoriteAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "app_key",
        "view_key",
        "name",
        "is_default",
        "per_page",
    )
    list_filter = ("app_key", "view_key", "is_default")
    search_fields = ("user__username", "name", "app_key", "view_key")
    ordering = ("user__username", "app_key", "view_key", "name")
    autocomplete_fields = ("user",)

    fieldsets = (
        (None, {"fields": ("user", "app_key", "view_key", "name")}),
        ("Preferences", {"fields": ("filters", "sort_by", "per_page", "is_default")}),
    )
