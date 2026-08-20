# accounts/views.py
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from equipment.models.request_equipment_models import (
    LocationTagChangeRequest,
    EquipmentChangeRequest,
)
from accounts.models import Department

User = get_user_model()


class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "registration/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user





        if user.is_staff or user.is_superuser:
            location_tag_requests = LocationTagChangeRequest.objects.filter(status="pending").order_by("-requested_at")[:100]
            equipment_requests = (
                EquipmentChangeRequest.objects
                .filter(status="pending")
                .select_related("requested_by", "equipment")
                .prefetch_related("document_requests")
                .order_by("-requested_at")[:100]
            )
            context["location_tag_requests"] = location_tag_requests
            context["equipment_requests"] = equipment_requests
            context["document_requests"] = [] #document_requests

            # ✅ TOTAL COUNT
            context["total_asset_requests"] = (
                LocationTagChangeRequest.objects.filter(status="pending").count()
                + EquipmentChangeRequest.objects.filter(status="pending").count()
            )

        return context


# --------------- Autocomplete user ------------
@login_required
def user_autocomplete(request):
    q = request.GET.get("q", "").strip()

    users = User.objects.filter(
        is_active=True,
        personnel_number__istartswith=q
    ).order_by("personnel_number")[:10]

    results = [
        {
            "id": user.pk,
            "text": f"{user.personnel_number} - {user.get_full_name() or user.username}",
        }
        for user in users
    ]

    return JsonResponse({"results": results})



@login_required
def department_autocomplete(request):
    """
    Select2-compatible autocomplete endpoint.

    Searches active departments by department code or department name.
    `id` is the Department primary key, which is department_code.
    """
    q = request.GET.get("q", "").strip()

    departments = (
        Department.objects
        .filter(is_active=True)
        .filter(
            Q(department_code__icontains=q) |
            Q(name__icontains=q)
        )
        .order_by("department_code")[:10]
    )

    results = [
        {
            "id": department.pk,  # department_code, because it is the PK
            "text": f"{department.department_code} - {department.name}",
        }
        for department in departments
    ]

    return JsonResponse({"results": results})