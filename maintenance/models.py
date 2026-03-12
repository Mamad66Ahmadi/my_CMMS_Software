# from django.db import models
# from viewflow.fsm import FSMField, transition
# from accounts.models import Department  # Import Department from accounts app


# # Create your models here.
# # ----------------------    Object Criticality    ----------------------------------
# class ObjectCriticality(models.Model):
#     obj_criticality = models.CharField(max_length=50, unique=True)
#     def __str__(self):
#         return self.obj_criticality
#     class Meta:
#         verbose_name = "Object Criticality"
#         verbose_name_plural = "Object Criticalities"


# # ----------------------    Object Type     ----------------------------------
# class ObjectType(models.Model):
#     obj_type = models.CharField(max_length=50, unique=True)
#     def __str__(self):
#         return self.obj_type
#     class Meta:
#         verbose_name = "Object Type"
#         verbose_name_plural = "Object Types"


# # ----------------------    Object Unit     ----------------------------------
# class Unit(models.Model):
#     unit_code = models.CharField(max_length=50, unique=True)
#     unit_description = models.CharField(max_length=100, null=True, blank=True)
#     def __str__(self):
#         return self.unit_code
#     class Meta:
#         verbose_name = "Unit"
#         verbose_name_plural = "Units"


# # ----------------------    Objects     ----------------------------------
# class FunctionalLocation(models.Model):
#     """ 
#     Represents the 'Place' or Position in the hierarchy (e.g., 103-K-101)
#     """
#     loc_tag = models.CharField(max_length=50, unique=True) 
#     loc_parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    
#     # Attributes describing the position
#     obj_criticality = models.ForeignKey(ObjectCriticality, on_delete=models.SET_NULL, null=True, blank=True, related_name='locations')
#     obj_type = models.ForeignKey(ObjectType, on_delete=models.SET_NULL, null=True, blank=True, related_name='locations')
#     obj_category = models.CharField(max_length=50, null=True, blank=True)
#     obj_description = models.CharField(max_length=100, null=True, blank=True)
#     long_tag = models.CharField(max_length=250, null=True, blank=True)
#     obj_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='locations')
#     obj_train = models.IntegerField(null=True, blank=True)
#     obj_note = models.CharField(max_length=250, null=True, blank=True)
#     obj_MIH_level = models.CharField(max_length=150, null=True, blank=True)
    
#     # System fields
#     obj_reg_date = models.DateTimeField(auto_now_add=True)
#     obj_reg_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_locations')

#     def __str__(self):
#         return self.loc_tag
#     class Meta:
#         ordering = ['loc_tag']


# class Equipment(models.Model):
#     """ 
#     Represents the physical 'Thing' installed at a location 
#     (e.g., Pump with Serial Number SN-1256365)
#     """
#     equipment_sn = models.CharField(max_length=50, unique=True, verbose_name="Serial Number")
#     # Link to where this equipment is currently installed
#     location = models.ForeignKey(FunctionalLocation, on_delete=models.SET_NULL, null=True, related_name='installed_equipments')
    
#     # System fields
#     eqp_reg_date = models.DateTimeField(auto_now_add=True)
#     eqp_reg_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_equipments')

#     def __str__(self):
#         return f"{self.location} ({self.equipment_sn})" if self.location else self.equipment_sn

#     class Meta:
#         verbose_name = "Equipment"
#         verbose_name_plural = "Equipments"
#         ordering = ['location']


# # ----------------------    Work Orders     ----------------------------------
# class WorkOrder(models.Model):
#     obj_tag = models.ForeignKey(Object, on_delete=models.CASCADE, related_name='obj_tag')
#     task = models.IntegerField()
#     directive = models.CharField(max_length=255)
#     description = models.TextField()
#     department_requester = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='requested_dep')
#     department_executive = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='executive_dep')
#     work_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_work_order')
#     status = FSMField(
#         default='draft', 
#         protected=True,  # Prevents direct modification of the state in DB
#         choices=[
#             ('draft', 'Draft'),
#             ('planned', 'Planned'),
#             ('released', 'Released'),
#             ('started', 'Started'),
#             ('reported', 'Reported'),
#             ('finished', 'Finished'),
#         ],)
#     plan_start = models.DateTimeField(null=True, blank=True)
#     plan_finish = models.DateTimeField(null=True, blank=True)
#     actual_start = models.DateTimeField(null=True, blank=True)
#     actual_finish = models.DateTimeField(null=True, blank=True)
#     reg_date = models.DateTimeField(auto_now_add=True)
#     reg_by = models.ForeignKey(User, on_delete=models.PROTECT,related_name='created_work_orders')
#     modified_date = models.DateField(auto_now=True)
#     modified_by = models.ForeignKey(User, on_delete=models.PROTECT,related_name='modified_work_orders')
#     def __str__(self):
#         return f"{self.id} - {self.task}"
#     class Meta:
#         verbose_name = "Work Order"
#         verbose_name_plural = "Work Orders"
#         ordering = ['-id']
#     # ---------------------- FSM Transitions ----------------------
    
#     @transition(field=status, source='draft', target='planned')
#     def plan(self):
#         """
#         Transition: Draft -> Planned
#         Logic: Resources are allocated, dates are set.
#         """
#         pass

#     @transition(field=status, source='planned', target='released')
#     def release(self):
#         """
#         Transition: Planned -> Released
#         Logic: Work order is officially released to the execution team.
#         """
#         pass

#     @transition(field=status, source='released', target='started')
#     def start(self):
#         """
#         Transition: Released -> Started
#         Logic: Work has begun on the object.
#         """
#         # You can add logic here to automatically set actual_start if needed
#         # from django.utils import timezone
#         # self.actual_start = timezone.now()
#         pass

#     @transition(field=status, source='started', target='reported')
#     def report(self):
#         """
#         Transition: Started -> Reported
#         Logic: Work is done, and the leader reports completion (pending final check).
#         """
#         pass

#     @transition(field=status, source='reported', target='finished')
#     def finish(self):
#         """
#         Transition: Reported -> Finished
#         Logic: Work order is closed and archived.
#         """
#         pass

#     # Optional: Allow returning to a previous state if needed (e.g., rejection)
#     @transition(field=status, source='released', target='planned')
#     def reject(self):
#         """
#         Transition: Released -> Planned
#         Logic: Work order was rejected or needs re-planning.
#         """
#         pass


# # ----------------------    Work Order Header (The Parent)    ----------------------------------
# class WorkOrderHeader(models.Model):
#     """
#     Represents the main Work Order (The Fault).
#     This holds the WO Number and the Object (Equipment).
#     """
#     # Auto-increment WO Number (e.g., 1001, 1002)
#     wo_number = models.AutoField(primary_key=True, verbose_name="WO Number")
    
#     obj_tag = models.ForeignKey(
#         Object, 
#         on_delete=models.CASCADE, 
#         related_name='work_order_headers'
#     )
    
#     # Optional: Description of the overall fault
#     fault_description = models.TextField(blank=True, null=True)

#     # System Fields
#     reg_date = models.DateTimeField(auto_now_add=True)
#     reg_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_headers')

#     def __str__(self):
#         return f"WO-{self.wo_number}"

#     class Meta:
#         verbose_name = "Work Order Header"
#         verbose_name_plural = "Work Order Headers"
#         ordering = ['-wo_number']


# # ----------------------    Work Order Task (The Child)    ----------------------------------
# class WorkOrderTask(models.Model):
#     """
#     Represents individual tasks within a Work Order.
#     Task 1, Task 2, etc.
#     """
#     # Link to the Parent Header
#     wo_header = models.ForeignKey(
#         WorkOrderHeader, 
#         on_delete=models.CASCADE, 
#         related_name='tasks'
#     )
    
#     # Auto-increment Task Number (1, 2, 3...)
#     task = models.IntegerField()
    
#     directive = models.CharField(max_length=255)
#     description = models.TextField()
    
#     department_requester = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='requested_tasks')
#     department_executive = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='executive_tasks')
#     work_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_tasks')
    
#     status = FSMField(
#         default='draft', 
#         protected=True,
#         choices=[
#             ('draft', 'Draft'),
#             ('planned', 'Planned'),
#             ('released', 'Released'),
#             ('started', 'Started'),
#             ('reported', 'Reported'),
#             ('finished', 'Finished'),
#         ],
#     )
    
#     plan_start = models.DateTimeField(null=True, blank=True)
#     plan_finish = models.DateTimeField(null=True, blank=True)
#     actual_start = models.DateTimeField(null=True, blank=True)
#     actual_finish = models.DateTimeField(null=True, blank=True)
    
#     reg_date = models.DateTimeField(auto_now_add=True)
#     reg_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_tasks')
#     modified_date = models.DateField(auto_now=True)
#     modified_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='modified_tasks')

#     def __str__(self):
#         return f"WO-{self.wo_header.wo_number} / Task {self.task}"

#     class Meta:
#         verbose_name = "Work Order Task"
#         verbose_name_plural = "Work Order Tasks"
#         # Ensure we don't have duplicate task numbers for the same header
#         unique_together = ('wo_header', 'task') 
#         ordering = ['-wo_header__wo_number', '-task']

#     def save(self, *args, **kwargs):
#         """
#         Override save to automatically calculate the next Task Number.
#         """
#         if self.wo_header and not self.task:
#             # Get the highest task number for this specific Work Order Header
#             last_task = WorkOrderTask.objects.filter(wo_header=self.wo_header).order_by('-task').first()
            
#             if last_task:
#                 self.task = last_task.task + 1
#             else:
#                 # If this is the first task, start at 1
#                 self.task = 1
        
#         super().save(*args, **kwargs)

#     # ---------------------- FSM Transitions ----------------------
    
#     @transition(field=status, source='draft', target='planned')
#     def plan(self):
#         if not self.plan_start:
#             self.plan_start = timezone.now()

#     @transition(field=status, source='planned', target='released')
#     def release(self):
#         pass

#     @transition(field=status, source='released', target='started')
#     def start(self):
#         if not self.actual_start:
#             self.actual_start = timezone.now()

#     @transition(field=status, source='started', target='reported')
#     def report(self):
#         pass

#     @transition(field=status, source='reported', target='finished')
#     def finish(self):
#         if not self.actual_finish:
#             self.actual_finish = timezone.now()

#     @transition(field=status, source='released', target='planned')
#     def reject(self):
#         pass