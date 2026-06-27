# work_orders/services/wo_filter_choices.py

from work_orders.models import Priority, Symptom, ProjectCode, DetectionMethod, WorkType, Cause
from work_orders.models.wo_status_models import WorkOrderStatus

def build_filter_choices_map():
    """Fetches all necessary choices for filter dropdowns."""
    # Fetch querysets once
    priorities        = Priority.objects.all().order_by("priority_level")
    symptoms          = Symptom.objects.all().order_by("symptom_code")
    project_codes     = ProjectCode.objects.all().order_by("project_code")
    detection_methods = DetectionMethod.objects.all().order_by("detection_code")
    work_types        = WorkType.objects.all().order_by("work_type_code")
    causes            = Cause.objects.all().order_by("cause_code")

    choices_map = {
        'status':           [("ALL", "All Statuses")]+list(WorkOrderStatus.choices),
        'priority':         [(str(p.pk), str(p)) for p in priorities],
        'symptom':          [(str(s.pk), str(s)) for s in symptoms],
        'cause':            [(str(c.pk), str(c)) for c in causes],
        'project_code':     [(str(pc.pk), str(pc)) for pc in project_codes],
        'detection_method': [(str(dm.pk), str(dm)) for dm in detection_methods],
        'work_type':        [(str(wt.pk), str(wt)) for wt in work_types],
    }
    return choices_map
