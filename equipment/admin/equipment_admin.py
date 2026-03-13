from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from ..models import (
    Equipment, EquipmentDocument
)
from base_admin_mixin import *


# ----------------------    Equipment Document inline Admin    ----------------------------------
class EquipmentDocumentInline(admin.TabularInline):
    """
    Displays Document records inside the Equipment admin page.
    """
    model = EquipmentDocument
    fields = ('file_name', 'file_link', 'description')
    readonly_fields = ('file_link', 'file_name', 'description') 
    extra = 0 
    can_add = False 
    can_delete = True 

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 View File</a>', obj.file.url)
        return "No File"
    file_link.short_description = 'File'


# ----------------------    Equipment Admin    ----------------------------------
@admin.register(Equipment)
class EquipmentAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('id', 'functional_location', 'serial_number', 'manufacturer', 'is_active')
    list_filter = ('functional_location__obj_type', 'manufacturer', 'is_active')
    search_fields = ('id', 'serial_number', 'functional_location__loc_tag', 'manufacturer', 'model')
    
    autocomplete_fields = ('functional_location',)
    inlines = [EquipmentDocumentInline]



    fieldsets = (
        (None, {
            'fields': ('functional_location', 'serial_number')
        }),
        ('Manufacturer Details', {
            'fields': ('manufacturer', 'model')
        }),
        ('Notes', {
            'fields': ('note', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'created_by', 'modified_at', 'modified_by'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('functional_location', 'serial_number', 'manufacturer', 'model',),
        }),
    )
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']



# ----------------------    Equipment Document Admin    ----------------------------------
@admin.register(EquipmentDocument)
class EquipmentDocumentAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('get_loc_tag', 'equipment_link', 'file_name', 'file_link')
    list_filter = ('equipment__functional_location__obj_type', 'created_at')
    
    search_fields = (
        'equipment__functional_location__loc_tag', 
        'file_name', 
        'equipment__serial_number', 
        'description'
    )
    
 
    autocomplete_fields = ('equipment',)
    
    fieldsets = (
        (None, {
            'fields': ('equipment', 'file_name', 'file', 'description')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'created_by', 'modified_at', 'modified_by'),
            'classes': ('collapse',),
        }),
    )

    def get_loc_tag(self, obj):
        if obj.equipment and obj.equipment.functional_location:
            return obj.equipment.functional_location.loc_tag
        return "No Location"
    get_loc_tag.short_description = 'Location Tag'
    get_loc_tag.admin_order_field = 'equipment__functional_location__loc_tag'

    def equipment_link(self, obj):
        if obj.equipment:
            url = reverse('admin:equipment_equipment_change', args=[obj.equipment.id])
            return format_html('<a href="{}">{} (ID: {})</a>', url, obj.equipment.serial_number or "No SN", obj.equipment.id)
        return "-"
    equipment_link.short_description = 'Equipment'

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Download</a>', obj.file.url)
        return "No File"
    file_link.short_description = 'File'

    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']



