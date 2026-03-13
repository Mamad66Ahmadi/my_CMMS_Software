from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from ..models import (
    ObjectCriticality, ObjectType, ObjectCategory, Unit,
    LocationTag,Equipment
)
# for importing data from my files
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

from .base_admin_mixin import *


# ----------------------    Equipment inline Admin    ----------------------------------
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


# ----------------------    Tags Resource Admin    ----------------------------------
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
