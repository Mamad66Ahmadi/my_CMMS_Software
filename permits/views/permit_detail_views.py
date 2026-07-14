# permits/views/permit_detail_views.py 


from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404

from permits.models.permit_models import Permit


class PermitDetailView(LoginRequiredMixin, DetailView):
    model = Permit
    template_name = "permits/permit_detail.html"
    context_object_name = "permit"
    slug_field = "permit_number"
    slug_url_kwarg = "permit_number"

    def get_queryset(self):
        return (
            Permit.objects.select_related(
                "location_tag",
                "work_order",
                "department",
                "authorized_issuer",
                "permit_holder",
                "created_by",
                "modified_by",
                "continuation_of",
            )
            .prefetch_related(
                "hazard_codes",
                "continuations",  # reverse FK: permits continued from this one
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permit = self.object

        context["special_conditions"] = permit.special_conditions_summary
        context["is_currently_valid"] = permit.is_currently_valid

        return context
