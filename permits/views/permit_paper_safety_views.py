from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from permits.models import (
    Permit,
    PermitPaperSafetyPermit,
    PaperSafetyPermitType,
    PaperSafetyPermitWorkflowStep,
)
from permits.services.paper_safety_permit_service import (
    PaperSafetyPermitReviewService,
)


PAPER_SAFETY_FORMSET_PREFIX = "paper_safety_permits"


class BasePermitPaperSafetyPermitFormSet(BaseInlineFormSet):
    """Protect approved records and all records after main-permit activation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inactive types remain selectable for existing records, but cannot be
        # selected for newly added requirements.
        for form in self.forms:
            field = form.fields.get("safety_type")
            if field is None:
                continue
            current_id = form.instance.safety_type_id
            queryset = field.queryset.filter(is_active=True)
            if current_id:
                queryset = field.queryset.filter(Q(is_active=True) | Q(pk=current_id))
            field.queryset = queryset

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        permit_is_activated = bool(
            self.instance
            and self.instance.pk
            and self.instance.activated_at
        )

        for form in self.forms:
            cleaned_data = getattr(form, "cleaned_data", None)
            if not cleaned_data:
                continue

            is_deleted = cleaned_data.get("DELETE", False)
            is_existing = bool(form.instance.pk)

            if permit_is_activated and (form.has_changed() or is_deleted):
                raise ValidationError(
                    "Paper safety permits cannot be changed after the main permit is activated."
                )

            if (
                is_existing
                and form.instance.status
                == PaperSafetyPermitWorkflowStep.Status.ACTIVE
                and (form.has_changed() or is_deleted)
            ):
                raise ValidationError(
                    "An approved paper safety permit cannot be edited or removed. "
                    "Permit Office must reject it before it can be corrected."
                )


PermitPaperSafetyPermitFormSet = inlineformset_factory(
    Permit,
    PermitPaperSafetyPermit,
    formset=BasePermitPaperSafetyPermitFormSet,
    fields=(
        "safety_type",
        "safety_permit_number",
    ),
    extra=1,
    can_delete=True,
)


class PermitPaperSafetyPermitFormSetMixin:
    """Add paper safety-permit formset handling to Permit create/update views."""

    paper_safety_formset_class = PermitPaperSafetyPermitFormSet
    paper_safety_formset_prefix = PAPER_SAFETY_FORMSET_PREFIX

    def paper_safety_formset_was_submitted(self):
        management_key = f"{self.paper_safety_formset_prefix}-TOTAL_FORMS"
        return self.request.method == "POST" and management_key in self.request.POST

    def get_paper_safety_formset(self, *, instance=None):
        cached = getattr(self, "_paper_safety_formset", None)
        if cached is not None:
            return cached

        if instance is None:
            instance = getattr(self, "object", None) or Permit()

        kwargs = {
            "instance": instance,
            "prefix": self.paper_safety_formset_prefix,
        }
        if self.paper_safety_formset_was_submitted():
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES

        self._paper_safety_formset = self.paper_safety_formset_class(**kwargs)
        return self._paper_safety_formset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paper_safety_permit_formset"] = self.get_paper_safety_formset()
        context["paper_safety_permit_types"] = PaperSafetyPermitType.objects.filter(
            is_active=True
        )
        return context

    def validate_paper_safety_formset(self, *, permit):
        if not self.paper_safety_formset_was_submitted():
            return None

        formset = self.get_paper_safety_formset(instance=permit)
        if formset.is_valid():
            return formset
        return False

    @staticmethod
    def save_paper_safety_formset(*, formset, permit, user):
        formset.instance = permit
        instances = formset.save(commit=False)

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        for instance in instances:
            instance.permit = permit
            if not instance.pk:
                instance.created_by = user
            instance.modified_by = user
            instance.save()

        formset.save_m2m()


class PaperSafetyPermitReviewView(LoginRequiredMixin, View):
    """Approve or reject one paper safety permit from the normal permit UI."""

    def post(self, request, permit_number, paper_safety_permit_id):
        record = get_object_or_404(
            PermitPaperSafetyPermit.objects.select_related("permit", "current_step"),
            pk=paper_safety_permit_id,
            permit__permit_number=permit_number,
        )

        action = (request.POST.get("action") or "").strip().lower()
        comment = (request.POST.get("review_comment") or "").strip()

        try:
            if action == "approve":
                submitted_number = request.POST.get("safety_permit_number")
                PaperSafetyPermitReviewService.approve(
                    paper_safety_permit_id=record.pk,
                    actor=request.user,
                    safety_permit_number=submitted_number,
                    comment=comment,
                )
                messages.success(
                    request,
                    "Paper safety permit approved.",
                )
            elif action == "reject":
                PaperSafetyPermitReviewService.reject(
                    paper_safety_permit_id=record.pk,
                    actor=request.user,
                    comment=comment,
                )
                messages.success(
                    request,
                    "Paper safety permit rejected.",
                )
            else:
                raise ValidationError("Invalid paper safety-permit review action.")

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to review this paper safety permit.",
            )
        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        if request.headers.get("HX-Request"):
            permits = list(
                record.permit.paper_safety_permits.select_related(
                    "safety_type", "current_step"
                ).prefetch_related("status_history")
            )
            labels = PermitPaperSafetyPermit.status_labels()
            for item in permits:
                item.prefetched_status_history = list(item.status_history.all())
                for event in item.prefetched_status_history:
                    event.from_status_label = labels.get(event.from_status, "Initial") if event.from_status else "Initial"
                    event.to_status_label = labels.get(event.to_status, event.to_status)
            return render(request, "permits/permit_detail_partials/paper_safety_permits_panel.html", {
                "permit": record.permit,
                "paper_safety_permits": permits,
                "paper_safety_permit_total_count": len(permits),
                "paper_safety_permit_active_count": sum(item.status == PaperSafetyPermitWorkflowStep.Status.ACTIVE for item in permits),
                "paper_safety_permit_deactive_count": sum(item.status == PaperSafetyPermitWorkflowStep.Status.DEACTIVE for item in permits),
                "paper_safety_permits_ready": record.permit.safety_permits_ready_for_activation,
                "can_review_paper_safety_permits": PaperSafetyPermitReviewService.actor_can_review(record=record, actor=request.user),
                "messages": messages.get_messages(request),
            })
        return redirect(
            "permits:permit_detail",
            permit_number=record.permit.permit_number,
        )
