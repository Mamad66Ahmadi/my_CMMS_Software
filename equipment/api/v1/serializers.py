# equipment/api/v1/serializers.py
from rest_framework import serializers
from equipment.models import (
    LocationTag, 
    ObjectType, 
    ObjectCriticality, 
    Unit,
    ObjectCategory,
    Equipment,
    EquipmentDocument
)

class ObjectCriticalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectCriticality
        fields = [
            'id',
            'obj_crt_level',
        ]
        depth = 0

class ObjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectType
        fields = [
            'id',
            'obj_type',
        ]
        depth = 0

class ObjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectCategory
        fields = [
            'id',
            'category_name',
        ]
        depth = 0

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = [
            'id',
            'unit_code',
        ]
        depth = 0

class LocationTagSerializer(serializers.ModelSerializer):

    relative_url = serializers.URLField(source='get_absolute_api_url', read_only=True)
    absolute_url = serializers.SerializerMethodField(method_name='get_abs_url')
    
    class Meta:
        model = LocationTag
        fields = [
            'loc_tag',
            'parent',
            'long_tag',
            'description',
            'obj_type',
            'obj_criticality',
            'obj_category',
            'unit',
            'train',
            'is_active',
            'created_at',
            'modified_at',
            'created_by',
            'modified_by',
            'relative_url',
            'absolute_url'
        ]
        depth = 0

        read_only_fields = ['created_by', 'modified_by', 'created_at', 'modified_at']
    
    def get_abs_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_api_url())
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        
        if instance.obj_type:
            rep['obj_type'] = ObjectTypeSerializer(instance.obj_type, context={'request':request}).data
        else:
            rep['obj_type'] = None
        
        if instance.obj_criticality:
            rep['obj_criticality'] = ObjectCriticalitySerializer(instance.obj_criticality, context={'request':request}).data
        else:
            rep['obj_criticality'] = None
        
        if instance.obj_category:
            rep['obj_category'] = ObjectCategorySerializer(instance.obj_category, context={'request':request}).data
        else:
            rep['obj_category'] = None
        
        if instance.unit:
            rep['unit'] = UnitSerializer(instance.unit, context={'request':request}).data
        else:
            rep['unit'] = None

        if instance.parent:
            rep['parent'] = instance.parent.loc_tag  # This is the key fix
        else:
            rep['parent'] = None


        # In detail view (with loc_tag in URL), remove relative_url
        #print(request.__dict__)

        if request.parser_context.get('kwargs').get('loc_tag'):
            rep.pop('relative_url', None)

        else:
            rep.pop('long_tag', None)
            rep.pop('description', None)
            rep.pop('obj_category',None)
            rep.pop('created_at',None)
            rep.pop('modified_at',None)
            rep.pop('created_by',None)
            rep.pop('modified_by',None)
        
        return rep
    
    def create(self, validated_data):
        # ✅ CONVERT TO UPPERCASE BEFORE SAVING
        if 'loc_tag' in validated_data:
            validated_data['loc_tag'] = validated_data['loc_tag'].upper()

        # Get current user from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):

        # Get current user from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['modified_by'] = request.user
        return super().update(instance, validated_data)
    


class EquipmentSerializer(serializers.ModelSerializer):
    functional_location = LocationTagSerializer(read_only=True)
    
    class Meta:
        model = Equipment
        fields = [
            'id',
            'functional_location',
            'serial_number',
            'note',
            'manufacturer',
            'model',
            'created_at',
            'modified_at',
            'is_active'
        ]
        depth = 0

class EquipmentDocumentSerializer(serializers.ModelSerializer):
    equipment = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EquipmentDocument
        fields = [
            'id',
            'equipment',
            'file_name',
            'file',
            'description',
            'created_at',
            'modified_at',
            'is_active'
        ]
        depth = 0
    
    def get_equipment(self, obj):
        if obj.equipment:
            return {
                'id': obj.equipment.id,
                'functional_location': obj.equipment.functional_location.loc_tag,
                'serial_number': obj.equipment.serial_number
            }
        return None
    
    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None

