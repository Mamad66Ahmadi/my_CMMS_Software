from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.exceptions import PermissionDenied


from work_orders.models import FaultReport,FaultReportStatus
from work_orders.forms import FaultReportCreateForm
from equipment.models import LocationTag

from django.contrib.auth import get_user_model
User = get_user_model()

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
        exclude_fault_id = request.GET.get("exclude_fault_id")  # <-- NEW

        faults = FaultReport.objects.none()

        if location_tag_id:
            faults = (
                FaultReport.objects
                .filter(
                    location_tag_id=location_tag_id,
                    status__in=["SUBMITTED", "APPROVED"],
                )
                .exclude(id=exclude_fault_id)  # <-- NEW: ignore current fault
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





from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView

class FaultReportReviewView(LoginRequiredMixin, UpdateView):
    model = FaultReport
    form_class = FaultReportCreateForm
    template_name = "work_orders/fault_reports/fault_report_review.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        obj = self.object

        is_method_or_staff = (
            user.is_staff or
            (user.department and user.department.name == "Method")
        )
        is_planner = getattr(user, "role", None) == "planner"

        is_supervisor = (
            user.role == "supervisor" and
            user.department == obj.reported_department
        )

        is_requester = user == obj.reported_by

        # --------------------------------
        # RULE 1: Staff / Method / Planner
        # --------------------------------
        if is_method_or_staff or is_planner:
            if obj.status == FaultReportStatus.CONVERTED:
                raise PermissionDenied("Converted reports cannot be edited.")
            # Note: Staff/Method/Planner can access SUBMITTED, APPROVED, and REJECTED reports.
            return super().dispatch(request, *args, **kwargs)

        # --------------------------------
        # RULE 2: Supervisor of requester department
        # --------------------------------
        if is_supervisor:
            if obj.status != FaultReportStatus.SUBMITTED:
                raise PermissionDenied("Supervisors can only access submitted reports.")
            return super().dispatch(request, *args, **kwargs)

        # --------------------------------
        # RULE 3: Requester
        # --------------------------------
        if is_requester:
            if obj.status != FaultReportStatus.SUBMITTED:
                raise PermissionDenied("Requesters can only access submitted reports.")
            return super().dispatch(request, *args, **kwargs)

        # --------------------------------
        # RULE 4: Everyone else
        # --------------------------------
        raise PermissionDenied()

    def form_valid(self, form):
        obj = form.save(commit=False)
        action = self.request.POST.get("action")
        user = self.request.user
        comment = self.request.POST.get("comment", "").strip()

        is_method_or_staff = (
            user.is_staff or
            (user.department and user.department.name == "Method")
        )
        is_planner = getattr(user, "role", None) == "planner"

        is_supervisor = (
            user.role == "supervisor" and
            user.department == obj.reported_department
        )

        is_requester = user == obj.reported_by

        # -------------------------------------------
        # SECURE WORKFLOW: RE-SUBMIT REJECTED REPORT
        # -------------------------------------------
        if action == "resubmit":
            # Double check current status is actually REJECTED
            if self.get_object().status != FaultReportStatus.REJECTED:
                raise PermissionDenied("Only rejected reports can be resubmitted.")
                
            if not (is_method_or_staff or is_planner):
                raise PermissionDenied("Only planners or staff can resubmit a rejected report.")

            obj.status = FaultReportStatus.SUBMITTED
            obj.save()
            messages.success(self.request, "Fault report status set back to 'Submitted'.")
            return redirect(self.get_success_url())

        # -------------------------------------------
        # REJECT VALIDATION
        # -------------------------------------------
        if action == "reject" and not comment:
            form.add_error(None, "Comment is required when rejecting a fault report.")
            return self.form_invalid(form)

        # Save other form edits
        obj.save()

        # -----------------------------
        # APPROVE
        # -----------------------------
        if action == "approve":
            if not (is_method_or_staff or is_supervisor or is_planner):
                raise PermissionDenied()

            obj.approve(user)
            messages.success(self.request, "Fault report approved.")

        # -----------------------------
        # REJECT
        # -----------------------------
        elif action == "reject":
            if not (is_method_or_staff or is_supervisor or is_requester or is_planner):
                raise PermissionDenied()

            obj.reject(user, comment)
            messages.warning(self.request, "Fault report rejected.")

        # -----------------------------
        # EDIT
        # -----------------------------
        else:
            messages.success(self.request, "Fault report updated.")

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("work_orders:fault_report_list")



