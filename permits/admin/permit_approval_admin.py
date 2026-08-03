from django.contrib import admin

from permits.models.approval_models import PermitApproval


@admin.register(PermitApproval)
class PermitApprovalAdmin(admin.ModelAdmin):
    """
    Minimal, safe admin registration for PermitApproval.

    Add list_display, filters, autocomplete fields, and fieldsets only after
    confirming the exact fields declared on the PermitApproval model.
    """

    list_per_page = 50
