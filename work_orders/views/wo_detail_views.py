# work_orders/views/wo_detail_views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from work_orders.models.wo_models import WorkOrder
# Add any other models needed here if they are not in models/__init__.py

@login_required
def work_order_detail_template(request, pk):
    """Renders the modal content for displaying detailed work order information."""
    wo = get_object_or_404(
        WorkOrder.objects.select_related(
            "fault_report", "location_tag", "location_tag__parent", "location_tag__unit",
            "equipment", "priority", "symptom", "project_code", "detection_method",
            "work_type", "reported_by", "reported_department", "modified_by",
            "parent_work_order",
        ).prefetch_related("tasks"),
        pk=pk,
    )

    return render(
        request,
        "work_orders/work_orders_head/_wo_detail_content.html",
        {"wo": wo},
    )
