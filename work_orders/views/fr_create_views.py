from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from work_orders.models import FaultReport, FaultReportStatus
from work_orders.forms import FaultReportCreateForm
from equipment.models import LocationTag
from work_orders.permissions.fault_report_permissions import FaultReportPermissions as FRP

from django.contrib.auth import get_user_model
User = get_user_model()


# -------------------------------------------------- Fault Create (Stage one) -------------------------------------------
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

        # project_code is saved automatically if included in FaultReportCreateForm
        obj.save()
        self.object = obj
        form.save_m2m()

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
        exclude_fault_id = request.GET.get("exclude_fault_id")

        faults = FaultReport.objects.none()

        if location_tag_id:
            faults = (
                FaultReport.objects
                .filter(
                    location_tag_id=location_tag_id,
                    status__in=["SUBMITTED", "APPROVED"],
                )
                .exclude(id=exclude_fault_id)
                .select_related(
                    "location_tag",
                    "equipment",
                    "project_code",
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


# ----------------------------------------- Supervisor Approve / Resubmit from reject View
class FaultReportReviewView(LoginRequiredMixin, UpdateView):
    model = FaultReport
    form_class = FaultReportCreateForm
    template_name = "work_orders/fault_reports/fault_report_review.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not FRP.can_review(request.user, self.object):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)

        action = self.request.POST.get("action")
        user = self.request.user
        comment = self.request.POST.get("comment", "").strip()

        # -----------------------------
        # RESUBMIT
        # -----------------------------
        if action == "resubmit":
            if not FRP.can_resubmit(user, obj):
                raise PermissionDenied()

            obj.resubmit(user)
            messages.success(self.request, "Fault report resubmitted.")
            return redirect(self.get_success_url())

        # -----------------------------
        # REJECT validation
        # -----------------------------
        if action == "reject" and not comment:
            form.add_error(None, "Comment is required when rejecting a fault report.")
            return self.form_invalid(form)

        # project_code is saved automatically if included in form
        obj.save()
        self.object = obj
        form.save_m2m()

        # -----------------------------
        # APPROVE
        # -----------------------------
        if action == "approve":
            if not FRP.can_approve(user, obj):
                raise PermissionDenied()

            obj.approve(user)
            messages.success(self.request, "Fault report approved.")

        # -----------------------------
        # REJECT
        # -----------------------------
        elif action == "reject":
            if not FRP.can_reject(user, obj):
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
        url = reverse_lazy("work_orders:fault_report_list")
        query = self.request.GET.urlencode()
        if query:
            url = f"{url}?{query}"
        return url


# -------------------------------------- Converting to the Work Order (last stage) view -------------------------
class FaultReportConvertView(LoginRequiredMixin, UpdateView):
    model = FaultReport
    form_class = FaultReportCreateForm
    template_name = "work_orders/fault_reports/fr_convert_to_wo.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not FRP.can_convert(request.user, self.object):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)

        # project_code is saved automatically if included in form
        obj.save()
        self.object = obj
        form.save_m2m()

        action = self.request.POST.get("action")
        comment = self.request.POST.get("comment", "").strip()
        user = self.request.user

        # -----------------------------
        # Reject
        # -----------------------------
        if action == "reject":
            if not comment:
                form.add_error(None, "Comment is required when rejecting.")
                return self.form_invalid(form)

            if not FRP.can_reject(user, obj):
                raise PermissionDenied()

            obj.reject(user, comment)
            messages.warning(self.request, "Fault report rejected.")
            return redirect(self.get_success_url())

        # -----------------------------
        # Convert
        # -----------------------------
        elif action == "convert":
            if not FRP.can_convert_action(user, obj):
                raise PermissionDenied()

            obj.mark_converted(user)
            messages.success(self.request, "Fault report converted to Work Order.")
            return redirect(self.get_success_url())

        # -----------------------------
        # Edit
        # -----------------------------
        else:
            messages.success(self.request, "Fault report updated.")
            return redirect(self.get_success_url())

    def get_success_url(self):
        url = reverse_lazy("work_orders:fault_report_list")
        query = self.request.GET.urlencode()
        if query:
            url = f"{url}?{query}"
        return url
