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

        # ADMIN: see all requests
        if user.is_staff or user.is_superuser:
            context["location_tag_requests"] = LocationTagChangeRequest.objects.filter(status="pending")
            context["equipment_requests"] = EquipmentChangeRequest.objects.filter(status="pending")
            context["document_requests"] = EquipmentDocumentChangeRequest.objects.filter(status="pending")

        else:
            # NORMAL USER: only their own requests
            context["location_tag_requests"] = LocationTagChangeRequest.objects.filter(
                requested_by=user
            )
            context["equipment_requests"] = EquipmentChangeRequest.objects.filter(
                requested_by=user
            )
            context["document_requests"] = EquipmentDocumentChangeRequest.objects.filter(
                requested_by=user
            )

        return context
