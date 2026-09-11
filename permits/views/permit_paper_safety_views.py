from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
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
from equipment.models.equipment_models import LocationTag
from permits.services.paper_safety_permit_service import (
    PaperSafetyPermitReviewService,
)
from permits.services.authorization_service import WorkflowAuthorizationService


PAPER_SAFETY_FORMSET_PREFIX = "paper_safety_permits"


def build_paper_safety_panel_context(*, permit, actor, message_storage):
    permits = list(
        permit.paper_safety_permits.select_related(
            "safety_type", "current_step"
        ).prefetch_related("status_history")
    )
    for item in permits:
        item.prefetched_status_history = list(item.status_history.all())
        for event in item.prefetched_status_history:
            event.from_status_label = event.from_status or "Initial"
            event.to_status_label = event.to_status

    can_edit = WorkflowAuthorizationService.actor_can_edit_permit(
        actor=actor,
        permit=permit,
    )
    return {
        "permit": permit,
        "paper_safety_permits": permits,
        "paper_safety_permit_total_count": len(permits),
        "paper_safety_permit_blocking_count": sum(
            item.blocks_main_permit for item in permits
        ),
        "paper_safety_permit_non_blocking_count": sum(
            not item.blocks_main_permit for item in permits
        ),
        "paper_safety_permits_ready": (
            permit.safety_permits_ready_for_activation
        ),
        "paper_safety_workflow_steps": (
            PaperSafetyPermitWorkflowStep.objects.filter(is_active=True)
            .order_by("step_order", "pk")
        ),
        "paper_safety_permit_types": (
            PaperSafetyPermitType.objects.filter(is_active=True)
            .order_by("sort_order", "name", "pk")
        ),
        "paper_safety_location_tags": LocationTag.objects.order_by("loc_tag"),
        "can_review_paper_safety_permits": bool(
            permits
            and PaperSafetyPermitReviewService.actor_can_review(
                record=permits[0],
                actor=actor,
            )
        ),
        "can_add_paper_safety_permits": can_edit and not permit.activated_at,
        "messages": message_storage,
    }


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
            location_field = form.fields.get("location_tag")
            if location_field is not None:
                location_field.required = not bool(form.instance.pk)
                if form.instance.pk:
                    location_field.disabled = True

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

            if is_existing and "location_tag" in form.changed_data:
                raise ValidationError(
                    "A paper safety permit location cannot be changed after submission."
                )

            if (
                is_existing
                and form.instance.current_step.name == "Activated"
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
        "location_tag",
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
        formset = self.get_paper_safety_formset()
        location_ids = {
            str(form["location_tag"].value())
            for form in formset.forms
            if form.fields.get("location_tag") and form["location_tag"].value()
        }
        location_labels = {
            str(location.pk): str(location)
            for location in LocationTag.objects.filter(pk__in=location_ids)
        }
        for form in formset.forms:
            location_value = form["location_tag"].value()
            form.location_tag_display = location_labels.get(
                str(location_value),
                str(form.instance.location_tag) if form.instance.location_tag else "",
            )

        context["paper_safety_permit_formset"] = formset
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

    def continuation_safety_permit_ids(self):
        """Return the existing safety permits selected for sharing on create."""
        values = self.request.POST.getlist("continuation_safety_permit_ids")
        return {int(value) for value in values if str(value).isdigit()}

    def link_continuation_safety_permits(self, *, permit, user):
        """Share selected existing safety-permit records with the new permit."""
        selected_ids = self.continuation_safety_permit_ids()
        continuation = permit.continuation_of
        if not selected_ids or not continuation:
            return

        allowed_ids = set(
            PermitPaperSafetyPermit.objects.filter(
                Q(permits=continuation) | Q(permit=continuation),
                pk__in=selected_ids,
            ).values_list("pk", flat=True)
        )
        if allowed_ids != selected_ids:
            raise ValidationError(
                "One or more selected continuation safety permits is invalid."
            )

        PermitPaperSafetyPermit.objects.filter(pk__in=allowed_ids).update(
            modified_by=user,
        )
        for safety_permit in PermitPaperSafetyPermit.objects.filter(pk__in=allowed_ids):
            safety_permit.permits.add(permit)

    @staticmethod
    def save_paper_safety_formset(*, formset, permit, user):
        formset.instance = permit
        instances = formset.save(commit=False)

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        for instance in instances:
            instance.permit = permit
            if not instance.location_tag_id:
                raise ValidationError("A location tag is required for every new safety permit.")
            if not instance.pk:
                instance.created_by = user
            instance.modified_by = user
            instance.save()
            instance.permits.add(permit)

        formset.save_m2m()


class PaperSafetyPermitReviewView(LoginRequiredMixin, View):
    """Change one paper safety permit's workflow step from the permit UI."""

    def post(self, request, permit_number, paper_safety_permit_id):
        record = get_object_or_404(
            PermitPaperSafetyPermit.objects.select_related("permit", "current_step"),
            pk=paper_safety_permit_id,
            permit__permit_number=permit_number,
        )

        action = (request.POST.get("action") or "").strip().lower()
        comment = (request.POST.get("review_comment") or "").strip()
        submitted_number = request.POST.get("safety_permit_number")

        try:
            if action == "change_step":
                updated_record = PaperSafetyPermitReviewService.assign_step(
                    paper_safety_permit_id=record.pk,
                    actor=request.user,
                    step_id=request.POST.get("step_id"),
                    safety_permit_number=submitted_number,
                    remarks=comment,
                )
                messages.success(
                    request,
                    f"Paper safety permit moved to {updated_record.current_step.name}.",
                )
            else:
                raise ValidationError("Invalid paper safety-permit workflow action.")

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
            return render(
                request,
                "permits/permit_detail_partials/paper_safety_permits_panel.html",
                build_paper_safety_panel_context(
                    permit=record.permit,
                    actor=request.user,
                    message_storage=messages.get_messages(request),
                ),
            )
        return redirect(
            "permits:permit_detail",
            permit_number=record.permit.permit_number,
        )


class PaperSafetyPermitCreateView(LoginRequiredMixin, View):
    """Add a required paper safety permit from the permit detail panel."""

    @transaction.atomic
    def post(self, request, permit_number):
        permit = get_object_or_404(
            Permit.objects.select_for_update().select_related(
                "current_step",
                "current_step__editable_role",
                "permit_type",
                "department",
                "location_tag",
                "location_tag__unit",
                "created_by",
            ),
            permit_number=permit_number,
        )

        try:
            WorkflowAuthorizationService.ensure_actor_can_edit_permit(
                actor=request.user,
                permit=permit,
            )
            if permit.activated_at:
                raise ValidationError(
                    "Paper safety permits cannot be added after the main permit is activated."
                )

            try:
                safety_type = PaperSafetyPermitType.objects.get(
                    pk=request.POST.get("safety_type"),
                    is_active=True,
                )
            except PaperSafetyPermitType.DoesNotExist as exc:
                raise ValidationError(
                    "Select an available paper safety-permit type."
                ) from exc

            if not request.POST.get("location_tag"):
                raise ValidationError("A location tag is required for every new safety permit.")

            PermitPaperSafetyPermit.objects.create(
                permit=permit,
                location_tag_id=request.POST.get("location_tag"),
                safety_type=safety_type,
                safety_permit_number=request.POST.get(
                    "safety_permit_number", ""
                ),
                created_by=request.user,
                modified_by=request.user,
            ).permits.add(permit)
            messages.success(request, "Paper safety permit added.")
        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to add a paper safety permit.",
            )
        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        if request.headers.get("HX-Request"):
            return render(
                request,
                "permits/permit_detail_partials/paper_safety_permits_panel.html",
                build_paper_safety_panel_context(
                    permit=permit,
                    actor=request.user,
                    message_storage=messages.get_messages(request),
                ),
            )
        return redirect(
            "permits:permit_detail",
            permit_number=permit.permit_number,
        )
