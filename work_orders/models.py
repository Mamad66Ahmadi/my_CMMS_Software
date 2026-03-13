from django.db import models
from viewflow.fsm import FSMField, transition
from django.utils import timezone
from django.contrib.auth import get_user_model

from equipment import LocationTag
from accounts.models import Department  # Import Department from accounts app (this app has User and Department models)


# ----------------------    Getting user model object    ----------------------------------
User = get_user_model()

# ----------------------    Work Order Header (The Parent)    ----------------------------------
class WorkOrderHeader(models.Model):
    """
    Represents the main Work Order (The Fault).
    This holds the WO Number and the Object (Equipment).
    """
    wo_number = models.AutoField(primary_key=True, verbose_name="WO Number")
    obj_tag = models.ForeignKey(LocationTag, on_delete=models.PROTECT, related_name='work_order_headers')
    
    fault_description = models.TextField()

    # System Fields
    reg_date = models.DateTimeField(auto_now_add=True)
    reg_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_headers')

    def __str__(self):
        return self.wo_number

    class Meta:
        verbose_name = "Work Order Header"
        verbose_name_plural = "Work Order Headers"
        ordering = ['-wo_number']


# ----------------------    Work Order Task (The Child)    ----------------------------------
class WorkOrderTask(models.Model):
    """
    Represents individual tasks within a Work Order.
    Task 1, Task 2, etc.
    """
    # Link to the Parent Header
    wo_header = models.ForeignKey(WorkOrderHeader, on_delete=models.CASCADE, related_name='tasks', verbose_name="WO Number")
    
    # Auto-increment Task Number (1, 2, 3...)
    task = models.IntegerField()
    
    directive = models.CharField(max_length=255)
    description = models.TextField()
    
    department_requester = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='requested_tasks')
    department_executive = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='executive_tasks')
    work_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_tasks')
    
    status = FSMField(
        default='draft', 
        protected=True,
        choices=[
            ('draft', 'Draft'),
            ('planned', 'Planned'),
            ('released', 'Released'),
            ('started', 'Started'),
            ('reported', 'Reported'),
            ('finished', 'Finished'),
        ],
    )
    
    reg_date = models.DateTimeField(auto_now_add=True)
    reg_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tasks')
    modified_date = models.DateField(auto_now=True)
    modified_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='modified_tasks')

    plan_start = models.DateTimeField(null=True, blank=True)
    plan_finish = models.DateTimeField(null=True, blank=True)
    planned_at = models.DateTimeField(null=True, blank=True)
    planned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='planned_tasks')

    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='released_tasks')

    actual_start = models.DateTimeField(null=True, blank=True)
    actual_finish = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='started_tasks')

    reported_at = models.DateTimeField(null=True, blank=True)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_tasks')

    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='finished_tasks')



    def __str__(self):
        return f"WO-{self.wo_header.wo_number} / Task {self.task}"

    class Meta:
        verbose_name = "Work Order Task"
        verbose_name_plural = "Work Order Tasks"
        unique_together = ('wo_header', 'task') 
        ordering = ['-wo_header__wo_number', '-task']

    def save(self, *args, **kwargs):
        """
        Override save to automatically calculate the next Task Number.
        """
        if self.wo_header and not self.task:
            # Get the highest task number for this specific Work Order Header
            last_task = WorkOrderTask.objects.filter(wo_header=self.wo_header).order_by('-task').first()
            
            if last_task:
                self.task = last_task.task + 1
            else:
                # If this is the first task, start at 1
                self.task = 1
        
        super().save(*args, **kwargs)

    # ---------------------- FSM Transitions ----------------------
    
    @transition(field=status, source='draft', target='planned')
    def plan(self, user=None):
        """Transition: Draft -> Planned"""
        self.planned_at = timezone.now()
        self.planned_by = user

    @transition(field=status, source='planned', target='draft')
    def plan_rework(self, user=None):
        """Transition: Planned -> Draft"""
        self.planned_at = None
        self.planned_by = None

    @transition(field=status, source='planned', target='released')
    def release(self, user=None):
        """Transition: Planned -> Released"""
        self.released_at = timezone.now()
        self.released_by = user

    @transition(field=status, source='released', target='planned')
    def release_rework(self, user=None):
        """Transition: Released -> Planned"""
        self.released_at = None
        self.released_by = None
        self.planned_at = timezone.now()
        self.planned_by = user

    @transition(field=status, source='released', target='started')
    def start(self, user=None):
        """Transition: Released -> Started"""
        self.started_at = timezone.now()
        self.started_by = user

    @transition(field=status, source='started', target='released')
    def start_rework(self, user=None):
        """Transition: Started -> Released"""
        self.started_at = None
        self.started_by = None
        self.released_at = timezone.now()
        self.released_by = user

    @transition(field=status, source='started', target='reported')
    def report(self, user=None):
        """Transition: Started -> Reported"""
        self.reported_at = timezone.now()
        self.reported_by = user

    @transition(field=status, source='reported', target='started')
    def report_rework(self, user=None):
        """Transition: Reported -> Started"""
        self.reported_at = None
        self.reported_by = None
        self.started_at = timezone.now()
        self.started_by = user

    @transition(field=status, source='reported', target='finished')
    def finish(self, user=None):
        """Transition: Reported -> Finished"""
        self.finished_at = timezone.now()
        self.finished_by = user

    @transition(field=status, source='finished', target='reported')
    def finish_rework(self, user=None):
        """Transition: Finished -> Reported"""
        self.finished_at = None
        self.finished_by = None
        self.reported_at = timezone.now()
        self.reported_by = user