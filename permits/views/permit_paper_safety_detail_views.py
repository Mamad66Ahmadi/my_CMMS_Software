from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from permits.models import PermitPaperSafetyPermit


class PaperSafetyPermitDetailView(LoginRequiredMixin, DetailView):
    model = PermitPaperSafetyPermit
    template_name = "permits/paper_safety_permit_detail.html"
    context_object_name = "safety_permit"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return (
            PermitPaperSafetyPermit.objects.select_related(
                "safety_type",
                "current_step",
                "location_tag",
                "location_tag__parent",
                "location_tag__unit",
                "permit",
                "created_by",
                "modified_by",
                "reviewed_by",
            )
            .prefetch_related(
                "permits",
                "status_history__changed_by",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_history"] = self.object.status_history.select_related(
            "changed_by"
        ).order_by("-changed_at", "-pk")
        context["primary_permit"] = self.object.permit
        return context
