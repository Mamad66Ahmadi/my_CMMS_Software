# permits/views/permit_detail_views.py 


from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, CreateView
from django.shortcuts import get_object_or_404
from django.urls import reverse

from permits.forms import PermitCreateForm
from permits.models import Permit, PermitStatus
from equipment.models import LocationTag


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



# ----------------- Create --------------------------------

class PermitCreateView(LoginRequiredMixin, CreateView):
    model = Permit
    form_class = PermitCreateForm
    template_name = "permits/permit_form.html"

    def get_initial(self):
        initial = super().get_initial()
        location_id = self.request.GET.get("location_tag")
        if location_id:
            initial["location_tag"] = location_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location_id = self.request.GET.get("location_tag") or self.request.POST.get("location_tag")

        if location_id:
            try:
                context["location"] = LocationTag.objects.get(pk=location_id)
            except LocationTag.DoesNotExist:
                pass

        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.status = PermitStatus.DRAFT
        obj.created_by = self.request.user
        obj.modified_by = self.request.user
        obj.save()
        form.save_m2m()
        self.object = obj
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("permits:permit_detail", kwargs={"permit_number": self.object.permit_number})