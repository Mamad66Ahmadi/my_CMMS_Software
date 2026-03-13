from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from ..models import (
    ObjectCriticality, ObjectType, ObjectCategory, Unit,
)
from base_admin_mixin import *


# ----------------------    Simple Lookups Admins    ----------------------------------

# ----------------------    Criticality Admins   ----------------------------------
@admin.register(ObjectCriticality)
class ObjectCriticalityAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('obj_crt_level', 'is_active')
    search_fields = ('obj_crt_level', 'description')
    list_filter = ('is_active',)
    # Define fields that should be read-only
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']


# ----------------------    Type Admins   ----------------------------------
@admin.register(ObjectType)
class ObjectTypeAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('obj_type', 'is_active')
    search_fields = ('obj_type',)
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']


# ----------------------    Category Admins   ----------------------------------
@admin.register(ObjectCategory)
class ObjectCategoryAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('category_name', 'is_active')
    search_fields = ('category_name',)
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']


# ----------------------    Unit Admins   ----------------------------------
@admin.register(Unit)
class UnitAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('unit_code', 'description', 'is_active')
    search_fields = ('unit_code', 'description')
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']
