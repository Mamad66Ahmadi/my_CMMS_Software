from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from permits.models import Permit, PermitAttachment
from permits.services.attachment_service import PermitAttachmentService
from permits.views.permit_detail_views import _render_detail_fragment


def _permit_url(permit):
    return reverse("permits:permit_detail", kwargs={"permit_number": permit.permit_number})


class PermitAttachmentDownloadView(LoginRequiredMixin, View):
    """Stream an attachment to any authenticated user with a valid permit link."""

    def get(self, request, permit_number, attachment_id):
        permit = get_object_or_404(Permit, permit_number=permit_number)
        attachment = get_object_or_404(
            PermitAttachment.objects.select_related("permit"),
            permit=permit,
            attachment_id=attachment_id,
        )
        if not PermitAttachmentService.actor_can_view(
            actor=request.user, attachment=attachment
        ):
            raise PermissionDenied
        if not attachment.file:
            raise PermissionDenied("This attachment has no file.")
        response = FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=Path(attachment.file.name).name,
        )
        return response


class PermitAttachmentCreateView(LoginRequiredMixin, View):
    """Create an attachment from a permit detail upload form."""

    def post(self, request, permit_number):
        permit = get_object_or_404(Permit, permit_number=permit_number)
        try:
            PermitAttachmentService.ensure_can_add(actor=request.user, permit=permit)
            upload = request.FILES.get("file")
            if not upload:
                raise ValidationError({"file": "Please select a file."})
            PermitAttachmentService.add(
                actor=request.user,
                permit=permit,
                file=upload,
                title=request.POST.get("title", ""),
                description=request.POST.get("description", ""),
            )
            messages.success(request, "Attachment uploaded successfully.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                permit.permit_number,
                "permits/permit_detail_partials/attachments_panel.html",
                {"attachments_panel_open": True},
            )
        return redirect(_permit_url(permit))


class PermitAttachmentUpdateView(LoginRequiredMixin, View):
    """Edit attachment metadata/file; restricted to Permit Office/superusers."""

    def post(self, request, permit_number, attachment_id):
        permit = get_object_or_404(Permit, permit_number=permit_number)
        attachment = get_object_or_404(PermitAttachment, permit=permit, attachment_id=attachment_id)
        try:
            PermitAttachmentService.change(
                actor=request.user,
                attachment=attachment,
                file=request.FILES.get("file") or attachment.file,
                title=request.POST.get("title", attachment.title),
                description=request.POST.get("description", attachment.description),
            )
            messages.success(request, "Attachment updated successfully.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                permit.permit_number,
                "permits/permit_detail_partials/attachments_panel.html",
                {"attachments_panel_open": True},
            )
        return redirect(_permit_url(permit))


class PermitAttachmentDeleteView(LoginRequiredMixin, View):
    """Delete an attachment; contributors may delete only their own uploads."""

    def post(self, request, permit_number, attachment_id):
        permit = get_object_or_404(Permit, permit_number=permit_number)
        attachment = get_object_or_404(PermitAttachment, permit=permit, attachment_id=attachment_id)
        try:
            PermitAttachmentService.remove(actor=request.user, attachment=attachment)
            messages.success(request, "Attachment deleted successfully.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                permit.permit_number,
                "permits/permit_detail_partials/attachments_panel.html",
                {"attachments_panel_open": True},
            )
        return redirect(_permit_url(permit))
