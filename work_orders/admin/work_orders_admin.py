from django.contrib import admin
from django.utils.html import format_html
from work_orders.models.wo_models import WorkOrder, WorkOrderTask
from work_orders.models.wo_status_models import WorkOrderStatus, TaskStatus

class WorkOrderTaskInline(admin.TabularInline):
    model = WorkOrderTask
    extra = 0
    fields = (
        'task_number', 'directive', 'status_badge', 'task_executing_department', 
        'planned_start', 'planned_finish'
    )
    readonly_fields = ('task_number', 'status_badge')
    show_change_link = True

    def status_badge(self, obj):
        if not obj.id: return "-"
        colors = {
            TaskStatus.CREATED: "#777",        # Grey
            TaskStatus.PLANNED: "#5bc0de",     # Blue
            TaskStatus.IN_PROGRESS: "#f0ad4e",  # Orange
            TaskStatus.COMPLETED: "#5cb85c",   # Green
            TaskStatus.APPROVED: "#0275d8",    # Dark Blue
            TaskStatus.CANCELLED: "#d9534f",   # Red
        }
        color = colors.get(obj.status, "#777")
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 4px; font-size: 10px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    # --- List View ---
    list_display = (
        'wo_number', 'location_tag', 'status_badge','parent_work_order', 'directive', 
        'priority','project_code', 'equipment', 'reported_department','reported_at'
    )
    list_filter = (
        'status', 'priority', 'work_type', 'reported_department', 
        'project_code', 'reported_at'
    )
    search_fields = (
        'wo_number', 'directive', 'fault_desc',
        'location_tag__loc_tag', 'equipment__serial_number',
        'reported_by__username', 'reported_by__first_name', 'reported_by__last_name'
    )
    list_select_related = (
        'equipment', 'location_tag', 'priority', 'reported_by', 
        'reported_department', 'project_code'
    )
    date_hierarchy = 'reported_at'
    ordering = ('-reported_at',)

    # --- Detail View ---
    readonly_fields = ('wo_number', 'reported_at', 'modified_at', 'task_status_summary_styled')
    
    autocomplete_fields = (
        'location_tag', 'equipment', 'priority', 'symptom', 'cause',
        'project_code', 'parent_work_order', 'detection_method', 
        'work_type', 'reported_by', 'reported_department', 'modified_by'
    )

    fieldsets = (
        ('General Information', {
            'fields': ('wo_number','parent_work_order', 'location_tag','equipment', 'status','task_status_summary_styled')
        }),
        ('Scope', {
            'fields': ('priority','directive', 'fault_desc', )
        }),
        ('Classification', {
            'fields': ('symptom', 'cause', 'cause_description', 'project_code', 'work_type', 'detection_method',)
        }),
        ('Metadata', {
            'fields': ('reported_by', 'reported_department', 'reported_at', 'modified_by', 'modified_at')
        }),
    )
    
    inlines = [WorkOrderTaskInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tasks')

    def status_badge(self, obj):
        colors = {
            WorkOrderStatus.CREATED: "#777",
            WorkOrderStatus.PLANNED: "#5bc0de",
            WorkOrderStatus.IN_EXECUTION: "#f0ad4e",
            WorkOrderStatus.WORK_DONE: "#5cb85c",
            WorkOrderStatus.CLOSED: "#0275d8",
            WorkOrderStatus.CANCELLED: "#d9534f",
        }
        color = colors.get(obj.status, "#777")
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 8px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def task_status_summary_styled(self, obj):
        return obj.task_status_summary
    task_status_summary_styled.short_description = "Task Summary"

@admin.register(WorkOrderTask)
class WorkOrderTaskAdmin(admin.ModelAdmin):
    # --- List View ---
    list_display = (
        'work_order',
        'task_number',
        'location_tag_display',
        'status_badge',
        'requester_dept_display',    # Updated
        'executing_dept_display',    # Updated
        'planned_start',
        'planned_finish',
        'actual_start',
        'actual_finish',
        'awaiting_reason',
    )

    # --- Renaming Methods ---
    def requester_dept_display(self, obj):
        return obj.task_requester_department
    requester_dept_display.short_description = "Requester Dep."
    requester_dept_display.admin_order_field = 'task_requester_department'

    def executing_dept_display(self, obj):
        return obj.task_executing_department
    executing_dept_display.short_description = "Executing Dep."
    executing_dept_display.admin_order_field = 'task_executing_department'


    search_fields = (
        'task_number',
        'work_order__wo_number',
        'work_order__location_tag__loc_tag',
        'directive',
    )

    list_filter = ('status', 'task_executing_department','task_requester_department', 'planned_start', 'planned_finish','actual_start','actual_finish','awaiting_reason' )

    list_select_related = (
        'work_order',
        'work_order__location_tag',
        'task_executing_department',
    )

    # Do not include work_order here permanently,
    # because it must be editable when creating a new task.
    readonly_fields = (
        'task_number',
        'location_tag_display',
        'created_at',
        'modified_at',
    )

    autocomplete_fields = (
        'work_order',
        'task_requester_department',
        'task_executing_department',
        'performed_action',
        'planner',
        'awaiting_reason',
        'work_master',
        'work_leader',
        'created_by',
        'modified_by',
    )

    fieldsets = (
        ('Task Identity', {
            'fields': (
                'work_order',
                'task_number',
                'is_main_task',
                'location_tag_display',
                'status',
                'directive',
                'description',
            )
        }),
        ('Departments', {
            'fields': (
                'task_requester_department',
                'task_executing_department',
            )
        }),
        ('Planning & Delays', {
            'fields': (
                'planner',
                'planned_start',
                'planned_finish',
                'awaiting_reason',
                'waiting_history',
                'remarks',
            )
        }),
        ('Audit & Staff', {
            'fields': (
                'work_master',
                'work_leader',
                'created_by',
                'created_at',
                'modified_by',
                'modified_at',
                'modified_itam',
            )
        }),

        ('Execution Details', {
            'fields': (
                'performed_action',
                'work_done_description',
                'permit',
                'actual_start',
                'actual_finish',
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))

        # If obj exists, we are editing an existing task.
        # In that case, prevent changing the related Work Order.
        if obj:
            readonly_fields.append('work_order')

        return readonly_fields

    def location_tag_display(self, obj):
        if not obj or not obj.work_order_id:
            return "-"

        if obj.work_order.location_tag:
            return obj.work_order.location_tag

        return "-"

    location_tag_display.short_description = "Location Tag"

    def status_badge(self, obj):
        colors = {
            TaskStatus.CREATED: "#777",
            TaskStatus.PLANNED: "#5bc0de",
            TaskStatus.IN_PROGRESS: "#f0ad4e",
            TaskStatus.COMPLETED: "#5cb85c",
            TaskStatus.APPROVED: "#0275d8",
            TaskStatus.CANCELLED: "#d9534f",
        }
        color = colors.get(obj.status, "#777")
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 8px;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = "Status"
