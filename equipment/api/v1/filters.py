# equipment/api/v1/filters.py
import django_filters
from equipment.models import LocationTag

class LocationTagFilter(django_filters.FilterSet):
    class Meta:
        model = LocationTag
        # ✅ FIX: Use list format (not dictionary) for browsable API
        fields = [
            'loc_tag',
            'parent__loc_tag',
            'obj_type__obj_type',
            'obj_criticality__obj_crt_level',
            'unit__unit_code',
            'train',
        ]