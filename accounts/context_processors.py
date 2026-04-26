# accounts/context_processors.py

from equipment.models.request_equipment_models import (
    LocationTagChangeRequest,
    EquipmentChangeRequest,
    EquipmentDocumentChangeRequest,
)


def pending_requests_count(request):
    if not request.user.is_authenticated:
        return {}

    if request.user.is_staff or request.user.is_superuser:
        location = LocationTagChangeRequest.objects.filter(status="pending").count()
        equipment = EquipmentChangeRequest.objects.filter(status="pending").count()
        document = EquipmentDocumentChangeRequest.objects.filter(status="pending").count()

        total = location + equipment + document

        return {"pending_requests_count": total}

    return {"pending_requests_count": 0}
