# permits/views/permit_workflow_views.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from permits.forms import PermitWorkflowDecisionForm
from permits.models import Permit
from permits.services.workflow_service import (
    PermitWorkflowService,
    WorkflowTransitionError,
)


class PermitWorkflowTransitionView(LoginRequiredMixin, View):
    """
    Handles workflow decisions for a permit.

    Important:
    - This view never updates Permit.current_step directly.
    - It delegates all workflow movement to PermitWorkflowService.
    """

    def post(self, request, permit_number):
        permit = get_object_or_404(
            Permit.objects.select_related(
                "workflow",
                "current_step",
                "current_step__editable_role",
                "current_step__editable_role__required_qualification",
                "permit_type",
            ),
            permit_number=permit_number,
        )

        form = PermitWorkflowDecisionForm(request.POST)

        if not form.is_valid():
            messages.error(
                request,
                "Invalid workflow action submission.",
            )
            return redirect(
                "permits:permit_detail",
                permit_number=permit.permit_number,
            )

        role_code = form.cleaned_data["role_code"]
        decision = form.cleaned_data["decision"]
        comment = form.cleaned_data.get("comment", "")

        try:
            result = PermitWorkflowService.transition(
                permit_id=permit.pk,
                actor=request.user,
                role_code=role_code,
                decision=decision,
                comment=comment,
            )

        except WorkflowTransitionError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to perform this workflow action.",
            )

        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        else:
            messages.success(
                request,
                (
                    f"Workflow action completed. "
                    f"Permit moved to: {result.permit.current_step.title}"
                ),
            )

        return redirect(
            "permits:permit_detail",
            permit_number=permit.permit_number,
        )
