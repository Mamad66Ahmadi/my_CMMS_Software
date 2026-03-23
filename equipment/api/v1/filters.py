# equipment/api/v1/filters.py

import django_filters
from equipment.models import LocationTag, ObjectType, ObjectCriticality, Unit



class LocationTagFilter(django_filters.FilterSet):
    # Dropdowns for foreign key fields
    obj_type = django_filters.ModelChoiceFilter(
        queryset=ObjectType.objects.all(),
        to_field_name='obj_type',  # Use this field for display
        label='Object Type'
    )
    obj_criticality = django_filters.ModelChoiceFilter(
        queryset=ObjectCriticality.objects.all(),
        to_field_name='obj_crt_level',
        label='Criticality'
    )

    unit_choices = [(unit.unit_code, unit.unit_code) for unit in Unit.objects.all()]

    unit = django_filters.MultipleChoiceFilter(
        field_name='unit__unit_code',  # CRITICAL FIX: This is the key
        choices=unit_choices,
        label='Unit'
    )
    
    # Text inputs for other fields
    loc_tag = django_filters.CharFilter(lookup_expr='icontains')
    parent__loc_tag = django_filters.CharFilter(lookup_expr='icontains')


    train_choices = [(str(i), str(i)) for i in range(1, 11)]
    train = django_filters.MultipleChoiceFilter(
        field_name='train',
        lookup_expr='in',
        choices=train_choices,
        label='Train'
    )    
    class Meta:
        model = LocationTag
        fields = [
            'loc_tag',
            'parent__loc_tag',
            'obj_type',
            'obj_criticality',
            'unit',
            'train',
            'is_active'
        ]