from django.contrib import admin


class AuditAdminMixin:
    list_per_page = 50
    save_on_top = True

    audit_field_names = (
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        model_field_names = {
            field.name for field in self.model._meta.get_fields()
        }
        readonly_fields.extend(
            field_name
            for field_name in self.audit_field_names
            if field_name in model_field_names
        )
        return tuple(dict.fromkeys(readonly_fields))

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "created_by_id") and not obj.created_by_id:
            obj.created_by = request.user
        if hasattr(obj, "modified_by_id"):
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if hasattr(instance, "created_by_id") and not instance.created_by_id:
                instance.created_by = request.user
            if hasattr(instance, "modified_by_id"):
                instance.modified_by = request.user
            instance.save()
        for deleted_object in formset.deleted_objects:
            deleted_object.delete()
        formset.save_m2m()
