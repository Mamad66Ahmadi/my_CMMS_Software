from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model
from django.urls import reverse




# ----------------------    Getting user model object    ----------------------------------
User = get_user_model()


# ----------------------    Abstract Base Class    ----------------------------------
class TimeStampedModel(models.Model):
    """
    An abstract base class that provides self-updating 
    'created' and 'modified' fields, plus audit trails.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Registration Date")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='%(app_label)s_%(class)s_created',
        verbose_name="Registered By"
    )
    modified_at = models.DateTimeField(auto_now=True, verbose_name="Last Modified")
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='%(app_label)s_%(class)s_modified',
        verbose_name="Modified By"
    )
    is_active = models.BooleanField(default=True)
    
    # Since inherit=True is used, all children will track history automatically.
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True


# ----------------------    Object Criticality    ----------------------------------
class ObjectCriticality(TimeStampedModel):
    obj_crt_level = models.CharField(max_length=50, unique=True, verbose_name="Criticality Level")
    description = models.TextField(blank=True, null=True)
    
    
    def __str__(self):
        return self.obj_crt_level 

    class Meta:
        verbose_name = "Object Criticality"
        verbose_name_plural = "Object Criticalities"
        ordering = ['obj_crt_level']


# ----------------------    Object Type     ----------------------------------
class ObjectType(TimeStampedModel):
    obj_type = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.obj_type 
    
    class Meta:
        verbose_name = "Object Type"
        verbose_name_plural = "Object Types"
        ordering = ['obj_type']


# ----------------------    Object Category     ----------------------------------
class ObjectCategory(TimeStampedModel):
    category_name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.category_name  

    class Meta:
        verbose_name = "Object Category"
        verbose_name_plural = "Object Categories"
        ordering = ['category_name']


# ----------------------    Object Unit     ----------------------------------
class Unit(TimeStampedModel):
    unit_code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return self.unit_code

    class Meta:
        verbose_name = "Unit"
        verbose_name_plural = "Units"
        ordering = ['unit_code']


# ----------------------    Location Tag     ----------------------------------
class LocationTag(TimeStampedModel):
    """ 
    Represents the 'Place' or Position in the hierarchy (e.g., 103-K-101)
    """
    loc_tag = models.CharField(max_length=50, unique=True)
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='children',
    )
    
    description = models.CharField(max_length=255, null=True, blank=True)
    long_tag = models.CharField(max_length=250, null=True, blank=True)
    
    # Foreign Keys
    obj_criticality = models.ForeignKey(ObjectCriticality, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    obj_type = models.ForeignKey(ObjectType, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    obj_category = models.ForeignKey(ObjectCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    train = models.IntegerField(null=True, blank=True)
    note = models.TextField(max_length=500, null=True, blank=True)
    mih_level = models.CharField(max_length=150, null=True, blank=True)
    
    def __str__(self):
        return self.loc_tag
    
    def get_absolute_api_url(self):
        """Return the API URL for this location tag"""
        return f'/equipment/api/v1/tag/{self.loc_tag}/'

    class Meta:
        verbose_name = "Location Tag"
        verbose_name_plural = "Location Tags"
        ordering = ['loc_tag']



# ----------------------    Equipment     ----------------------------------
class Equipment(TimeStampedModel):
    """ 
    Represents the physical 'Thing' installed at a location 
    """
    functional_location = models.ForeignKey(
        LocationTag, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='installed_equipments',
    )
    serial_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Serial Number")
    
    note = models.TextField(max_length=500, null=True, blank=True)
    manufacturer = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    #documents = models.FilePathField(blank=True, null=True)
    
    def __str__(self):
        loc_str = str(self.functional_location) if self.functional_location else "No Location"
        return f"{loc_str}/id:{self.id}"

    class Meta:
        ordering = ['functional_location', 'id']


# ----------------------    Equipment Document    ----------------------------------
def get_document_upload_path(instance, filename):
    """
    Helper function to determine upload path dynamically.
    Path: media/<loc_tag>/<filename>
    """
    # Safely get the location tag. If missing, use 'unassigned'.
    if instance.equipment.functional_location:
        loc_tag = instance.equipment.functional_location.loc_tag
    else:
        loc_tag = 'unassigned'
        
    return f'{loc_tag}/{filename}'

class EquipmentDocument(TimeStampedModel):
    """
    Represents a single document file attached to an Equipment.
    """

    equipment = models.ForeignKey(
        Equipment, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    file_name = models.CharField(unique=True)
    file = models.FileField(upload_to=get_document_upload_path, verbose_name="Document File")
    description = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        # Access location via the equipment relationship
        loc_tag = self.equipment.functional_location.loc_tag if self.equipment.functional_location else "Unknown"
        return f"Doc for {loc_tag}: {self.file_name or self.file.name}"    
    class Meta:
        verbose_name = "Equipment Document"
        verbose_name_plural = "Equipment Documents"
        ordering = ['equipment__functional_location__loc_tag', 'equipment']



