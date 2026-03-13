from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    ObjectCriticality, ObjectType, ObjectCategory, Unit,
    LocationTag, Equipment, EquipmentDocument
)
# for importing data from my files
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

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

# ----------------------    Simple Lookups Admins    ----------------------------------
@admin.register(ObjectCriticality)
class ObjectCriticalityAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('obj_crt_level', 'is_active')
    search_fields = ('obj_crt_level', 'description')
    list_filter = ('is_active',)
    # Define fields that should be read-only
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']

@admin.register(ObjectType)
class ObjectTypeAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('obj_type', 'is_active')
    search_fields = ('obj_type',)
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']

@admin.register(ObjectCategory)
class ObjectCategoryAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('category_name', 'is_active')
    search_fields = ('category_name',)
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']

@admin.register(Unit)
class UnitAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin):
    list_display = ('unit_code', 'description', 'is_active')
    search_fields = ('unit_code', 'description')
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']

# ----------------------    Location Tag Admin    ----------------------------------
class EquipmentInline(admin.TabularInline):
    """
    Displays Equipment records inside the LocationTag admin page.
    """
    model = Equipment
    # Show these columns in the inline table
    fields = ('id', 'serial_number', 'manufacturer', 'model')

    readonly_fields = ('id',)
    
    can_add = True 
    can_delete = True
    extra = 0 



# ----------------------    Equipment Admin    ----------------------------------
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
    
    # FIXED: Removed 'get_loc_tag' (method) and kept only valid database lookups
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




# ----------------------    Import Resource    ----------------------------------
class LocationTagResource(resources.ModelResource):
    # Map Excel Columns to Model Fields
    
    # 1. Direct Mappings
    loc_tag = Field(attribute='loc_tag', column_name='loc_tag')
    description = Field(attribute='description', column_name='description')
    long_tag = Field(attribute='long_tag', column_name='long_tag')
    note = Field(attribute='note', column_name='note')
    mih_level = Field(attribute='mih_level', column_name='mih_level')
    train = Field(attribute='train', column_name='train')
    
    # 2. Foreign Key Mappings (Lookups)
    obj_criticality = Field(
        attribute='obj_criticality', 
        column_name='obj_criticality',
        widget=ForeignKeyWidget(ObjectCriticality, 'obj_crt_level'),
        default=None # Handle missing criticality gracefully
    )
    
    obj_category = Field(
        attribute='obj_category', 
        column_name='obj_category',
        widget=ForeignKeyWidget(ObjectCategory, 'category_name'),
        default=None
    )
    
    obj_type = Field(
        attribute='obj_type', 
        column_name='obj_type',
        widget=ForeignKeyWidget(ObjectType, 'obj_type'),
        default=None
    )
    
    unit = Field(
        attribute='unit', 
        column_name='unit',
        widget=ForeignKeyWidget(Unit, 'unit_code'),
        default=None
    )
    
    # 3. Self-Referential Mapping (Parent)
    parent = Field(
        attribute='parent', 
        column_name='parent',
        widget=ForeignKeyWidget(LocationTag, 'loc_tag'),
        default=None # If parent is missing or not found, set to None
    )

    class Meta:
        model = LocationTag
        fields = (
            'loc_tag', 'description', 'long_tag', 'note', 'mih_level', 'train',
            'obj_criticality', 'obj_category', 'obj_type', 'unit', 'parent'
        )
        import_id_fields = ('loc_tag',)
        skip_unchanged = True
        use_bulk = True 

    # ----------------------    FIX: Data Cleaning    ----------------------------------
    def before_import_row(self, row, **kwargs):
        """
        This method runs for every row before it is saved.
        We use it to convert empty strings to None so Django doesn't crash.
        """
        # List of columns that are numbers or foreign keys
        # If they are empty strings in Excel, make them None.
        numeric_fields = ['train', 'parent', 'obj_criticality', 'obj_category', 'obj_type', 'unit']
        
        for field_name in numeric_fields:
            if field_name in row:
                # If the value is an empty string or just whitespace, set it to None
                if row[field_name] in [None, '']:
                    row[field_name] = None

# ----------------------    Location Tag Admin    ----------------------------------
@admin.register(LocationTag)
class LocationTagAdmin(ReadOnlyAdminMixin, SimpleHistoryAdmin,ImportExportModelAdmin): 

    resource_class = LocationTagResource

    list_display = ('loc_tag', 'parent', 'unit', 'train', 'is_active')
    list_filter = ('obj_type', 'unit', 'obj_criticality', 'is_active')
    search_fields = ('loc_tag', 'description', 'long_tag')

    autocomplete_fields = ('parent',)

    
    inlines = [EquipmentInline]
    
    fieldsets = (
        ('Location Properties', {
            'fields': ('loc_tag', 'parent', 'unit', 'train', 'long_tag') 
        }),
        ('Classification', {
            'fields': ('obj_criticality', 'obj_type', 'obj_category', 'description') 
        }),
        ('Details', {
            'fields': ('note', 'mih_level', 'is_active') 
        }),
        # 2. Add the Audit Information section back here
        ('Audit Information', {
            'fields': ('created_at', 'created_by', 'modified_at', 'modified_by'),
            'classes': ('collapse',),
        }),
    )
    
    audit_fields = ['created_at', 'created_by', 'modified_at', 'modified_by']
