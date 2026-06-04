from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages



from work_orders.models import FaultReport,FaultReportStatus
from work_orders.forms import FaultReportCreateForm
from equipment.models import LocationTag

#-------------------------------------------------- Fault Create (Stage one) -------------------------------------------
class FaultReportCreate(LoginRequiredMixin, CreateView):
    model = FaultReport
    form_class = FaultReportCreateForm
    template_name = "work_orders/fault_reports/fault_report_create.html"
    success_url = reverse_lazy("work_orders:fault_report_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location_id = self.request.GET.get("location_tag") or self.request.POST.get("location_tag")

        if location_id:
            try:
                context["location"] = LocationTag.objects.get(id=location_id)
            except LocationTag.DoesNotExist:
                pass

        return context

    def get_initial(self):
        initial = super().get_initial()
        location_id = self.request.GET.get("location_tag")
        if location_id:
            initial["location_tag"] = location_id
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.reported_by = self.request.user

        dept = self.request.user.department

        if dept is None:
            form.add_error(None, "Your user has no department set. Please contact admin.")
            return self.form_invalid(form)

        obj.reported_department = dept

        obj.status = FaultReportStatus.SUBMITTED
        
        obj.save()
        self.object = obj

        action = self.request.POST.get("_save_action")

        if action == "add_another":
            messages.success(self.request, "Fault report saved. You can create another one.")
            return redirect("work_orders:fault_report_add")

        messages.success(self.request, "Fault report saved successfully.")
        return redirect(self.get_success_url())





# ------------------------------------- Check for Duplicate Faults or Orders ------------------------------
class FaultsByLocationPartial(LoginRequiredMixin, View):
    template_name = "work_orders/fault_reports/existing_faults_table.html"

    def get(self, request, *args, **kwargs):
        location_tag_id = request.GET.get("location_tag")

        faults = FaultReport.objects.none()

        if location_tag_id:
            faults = (
                FaultReport.objects
                .filter(
                    location_tag_id=location_tag_id,
                    status__in=["SUBMITTED", "APPROVED"],
                )
                .select_related(
                    "location_tag",
                    "equipment",
                    "reported_by",
                    "reported_department",
                    "executing_department",
                    "planner",
                )
                .order_by("-reported_at")
            )

        context = {
            "faults": faults,
            "location_tag_id": location_tag_id,
        }
        return render(request, self.template_name, context)