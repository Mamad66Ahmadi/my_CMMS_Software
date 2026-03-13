# ----------------------    Base Admin Mixin    ----------------------------------
class ReadOnlyAdminMixin:
    """
    Mixin to automatically handle audit fields (created_by, modified_by)
    and make them read-only.
    """
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        
        obj.modified_by = request.user
        
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj) or []
        if hasattr(self, 'audit_fields'):
            return list(readonly_fields) + list(self.audit_fields)
        return readonly_fields