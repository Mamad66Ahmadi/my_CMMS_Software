from django.db import models
from simple_history.models import HistoricalRecords

from accounts.models import Department, User


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
    obj_criticality = models.ForeignKey(ObjectCriticality, on_delete=models.SET_NULL, null=True, blank=True, related_name='locations')
    obj_type = models.ForeignKey(ObjectType, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    obj_category = models.ForeignKey(ObjectCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    
    operational_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='tag_locations')
    train = models.IntegerField(null=True, blank=True)
    note = models.TextField(max_length=500, null=True, blank=True)
    mih_level = models.CharField(max_length=150, null=True, blank=True)
    
    def __str__(self):
        return self.loc_tag

    class Meta:
        ordering = ['loc_tag']



# ----------------------    Equipment     ----------------------------------
class Equipment(TimeStampedModel):
    """ 
    Represents the physical 'Thing' installed at a location 
    """
    equipment_id = models.AutoField()

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
    documents = models.FilePathField(blank=True, null=True)
    
    def __str__(self):
        loc_str = str(self.functional_location) if self.functional_location else "No Location"
        return f"{loc_str}/id:{self.equipment_id}"

    class Meta:
        ordering = ['functional_location', 'equipment_id']



