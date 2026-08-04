# permits/admin/base_admin.py


from django.contrib import admin

AUDIT_FIELDS = (
    "created_at",
    "created_by",
    "modified_at",
    "modified_by",
)

AUDIT_FIELDSET = (
    "Audit Information",
    {
        "classes": ("collapse",),
        "fields": AUDIT_FIELDS,
    },
)


class TimeStampedAdmin(admin.ModelAdmin):
    """
    Base admin that automatically populates created_by and modified_by
    from the current authenticated admin user.
    """
    readonly_fields = AUDIT_FIELDS

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "created_by") and not obj.created_by_id:
            obj.created_by = request.user

        if hasattr(obj, "modified_by"):
            obj.modified_by = request.user

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            if hasattr(obj, "deactivate"):
                obj.deactivate(user=request.user)
            else:
                obj.delete()

        for instance in instances:
            if hasattr(instance, "created_by") and not instance.created_by_id:
                instance.created_by = request.user

            if hasattr(instance, "modified_by"):
                instance.modified_by = request.user

            instance.save()

        formset.save_m2m()
