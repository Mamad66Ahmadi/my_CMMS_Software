# work_orders/views/wo_detail_views.py

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, UpdateView
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin

from work_orders.models.wo_models import WorkOrder, WorkOrderTask
from work_orders.forms import WorkOrderTaskForm



@login_required
def work_order_detail_template(request, pk):
    wo = get_object_or_404(
        WorkOrder.objects.select_related(
            "fault_report", "location_tag", "location_tag__parent", "location_tag__unit",
            "equipment", "priority", "symptom", "project_code", "detection_method",
            "work_type", "reported_by", "reported_department", "modified_by",
            "parent_work_order",
        ).prefetch_related(
            Prefetch(
                "tasks",
                queryset=WorkOrderTask.objects.select_related(
                    # adjust these to your actual FK field names on Task
                    "task_executing_department",
                    "task_requester_department",
                    "awaiting_reason",
                )
            )
        ),
        pk=pk,
    )

    return render(
        request,
        "work_orders/work_orders_head/_wo_detail_content.html",
        {"wo": wo},
    )





class WorkOrderTasksEditorView(LoginRequiredMixin, DetailView):
    """
    Renders the parent template container listing all tasks for the work order.
    """
    model = WorkOrder
    template_name = 'work_orders/work_orders_head/wo_tasks_editor.html'
    context_object_name = 'work_order'
    pk_url_kwarg = 'wo_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch tasks ordered by task_number to keep performance high
        context['tasks'] = self.object.tasks.all().order_by('task_number')
        return context


class TaskFormPartialUpdateView(LoginRequiredMixin, UpdateView):
    """
    AJAX Class-Based View to fetch/render the task form HTML (GET) 
    and validate/save task updates (POST).
    """
    model = WorkOrderTask
    form_class = WorkOrderTaskForm
    pk_url_kwarg = 'task_id'
    context_object_name = 'task'

    def render_to_json_response(self, form, success=True, errors=None, status_code=200):
        """Helper to render the partial HTML form and return a JsonResponse."""
        html = render_to_string(
            'work_orders/work_orders_head/components/_task_form_fields.html',
            {'form': form, 'task': self.object},
            request=self.request
        )
        
        response_data = {
            'success': success,
            'html': html
        }
        
        if errors:
            response_data['errors'] = errors
        if success:
            response_data['message'] = f"Task #{self.object.task_number} updated successfully!"
            response_data['task_label'] = f"Task #{self.object.task_number} - {self.object.get_status_display()}"
            
        return JsonResponse(response_data, status=status_code)

    def get(self, request, *args, **kwargs):
        """Returns the populated HTML form fragment for editing."""
        self.object = self.get_object()
        form = self.get_form()
        return self.render_to_json_response(form, success=True)

    def form_valid(self, form):
        """Processes valid submissions, sets audit trails, and returns success JSON."""
        self.object = form.save(commit=False)
        self.object.modified_by = self.request.user
        self.object.save()
        return self.render_to_json_response(form, success=True)

    def form_invalid(self, form):
        """Processes validation failures and returns error state with updated form rules."""
        return self.render_to_json_response(form, success=False, errors=form.errors, status_code=400)



# -------------------- Auto complete ------------------------
# -------------------- Auto complete ------------------------
@login_required
def work_order_autocomplete(request):
    q = request.GET.get("q", "").strip()

    if len(q) < 2:
        return JsonResponse({"results": []})

    work_orders = (
        WorkOrder.objects
        .filter(wo_number__icontains=q)
        .order_by("-reported_at")[:10]
    )

    results = [{"id": wo.id, "text": wo.wo_number} for wo in work_orders]
    return JsonResponse({"results": results})

