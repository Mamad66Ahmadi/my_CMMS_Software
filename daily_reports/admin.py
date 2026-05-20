# daily_reports/admin.py

from django.contrib import admin
from .models import DailyReport


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):

    # Hide auto-managed fields
    exclude = ('father_tag',)

    # Use autocomplete for large tables
    autocomplete_fields = ('location_tag',)

    # List page
    list_display = (
        'date',
        'location_tag',
        'location_tag__unit',
        'location_tag__train',
        'wo_number',
        'department',
        'status',
        'created_by'
    )

    list_filter = (
        'status',
        'date',
        'department',
    )

    search_fields = (
        'wo_number',
        'description',
        'employees',
        'location_tag__loc_tag',
    )

    date_hierarchy = "date"

    # Optional but useful in operations
    list_select_related = (
        'location_tag',
        'department',
        'created_by',
    )

    # Audit fields visible but not editable
    readonly_fields = (
        'created_at',
        'modified_at',
        'created_by',
        'modified_by',
    )

    fieldsets = (
        ('Work Information', {
            'fields': (
                'date',
                'location_tag',
                'wo_number',
                'status',
                'actual_start',
            )
        }),

        ('Work Description', {
            'fields': (
                'description',
                'employees',
            )
        }),

        ('Department', {
            'fields': (
                'department',
            )
        }),

        ('Audit Information', {
            'fields': (
                'created_at',
                'created_by',
                'modified_at',
                'modified_by',
            ),
            'classes': ('collapse',),
        }),
    )

    # ---------------- Pre-fill department ----------------
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        if hasattr(request.user, "department") and request.user.department:
            initial["department"] = request.user.department

        return initial

    # ---------------- Auto audit fields ----------------
    def save_model(self, request, obj, form, change):

        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.modified_by = request.user

        super().save_model(request, obj, form, change)
