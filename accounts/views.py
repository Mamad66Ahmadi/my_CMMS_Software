# accounts/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from equipment.models.request_equipment_models import (
    LocationTagChangeRequest,
    EquipmentChangeRequest,
    EquipmentDocumentChangeRequest,
)


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "registration/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user





        if user.is_staff or user.is_superuser:
            location_tag_requests = LocationTagChangeRequest.objects.filter(status="pending").order_by("-requested_at")[:100]
            equipment_requests = EquipmentChangeRequest.objects.filter(status="pending").order_by("-requested_at")[:100]
            document_requests = EquipmentDocumentChangeRequest.objects.filter(status="pending").order_by("-requested_at")[:100]

            context["location_tag_requests"] = location_tag_requests
            context["equipment_requests"] = equipment_requests
            context["document_requests"] = document_requests

            # ✅ TOTAL COUNT
            context["total_asset_requests"] = (
                LocationTagChangeRequest.objects.filter(status="pending").count()
                + EquipmentChangeRequest.objects.filter(status="pending").count()
                + EquipmentDocumentChangeRequest.objects.filter(status="pending").count()
            )

        return context



