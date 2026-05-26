from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Min, Max, Count, OuterRef, Subquery


from daily_reports.models import DailyReport
from equipment.models.equipment_models import LocationTag
from daily_reports.forms import DailyReportForm, LocationSearchForm

class DailyReportCreateView(LoginRequiredMixin, CreateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = "daily_reports/dr_create_form.html"
    success_url = reverse_lazy("daily_reports:report_list")

    def get(self, request, *args, **kwargs):
        location_id = request.GET.get('location_tag')

        # --- STEP 1: Search for Location ---
        if not location_id:
            form = LocationSearchForm()
            return render(request, "daily_reports/dr_step1_search.html", {'form': form})

        # --- STEP 2: Recent Reports Table ---
        mode = request.GET.get('mode')
        # We only show the table if mode is NOT 'new' and NOT 'continue'
        if not mode:
            location = get_object_or_404(LocationTag, id=location_id)
            
            # (Your existing grouping logic here...)
            latest_50_reports = DailyReport.objects.filter(
                location_tag=location,
                department=request.user.department
            ).order_by('-date', '-created_at')[:50]

            groups = {}
            for report in latest_50_reports:
                group_key = report.wo_number if report.wo_number else f"start_{report.actual_start}"
                if group_key not in groups:
                    groups[group_key] = {
                        'wo_number': report.wo_number,
                        'report_count': 0,
                        'earliest_start': report.actual_start,
                        'latest_date': report.date,
                        'last_description': report.description,
                        'last_status': report.status,
                        'last_id': report.id,
                        'sort_date': report.date 
                    }
                groups[group_key]['report_count'] += 1
                # ... (rest of your aggregation logic)

            processed_reports = sorted(groups.values(), key=lambda x: x['sort_date'], reverse=True)[:5]

            return render(request, "daily_reports/dr_step2_recent.html", {
                'location': location,
                'recent_reports': processed_reports
            })

        # --- STEP 3: The Actual Form ---
        # If code reaches here (meaning location_id exists AND mode exists), 
        # we MUST call super().get() to actually show the form.
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location_id = self.request.GET.get('location_tag')
        if location_id:
            # This allows us to use {{ location.tag_name }} in the template
            context['location'] = get_object_or_404(LocationTag, id=location_id)
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial["date"] = timezone.localdate()
        
        # Prefill from Step 1/2
        location_id = self.request.GET.get('location_tag')
        source_report_id = self.request.GET.get('source_report')
        mode = self.request.GET.get('mode')

        if location_id:
            location = get_object_or_404(LocationTag, id=location_id)
            initial['location_tag'] = location_id
            initial['location_tag_name'] = location.loc_tag
                    
        # If 'Continuous' mode and a report was selected, copy its values
        if mode == 'continue' and source_report_id:
            source_report = get_object_or_404(DailyReport, id=source_report_id)
            initial['wo_number'] = source_report.wo_number
            initial['actual_start'] = source_report.actual_start
            initial['employees'] = source_report.employees
            # initial['department'] = source_report.department # Uncomment if needed
            
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.request.user.department:
            raise PermissionDenied("Your account has no department.")
        
        # Ensure initial department is set from the user's profile
        kwargs['initial'] = kwargs.get('initial', {})
        kwargs['initial']['department'] = self.request.user.department
        return kwargs

    def form_valid(self, form):
        # 1. Create the instance but don't save to DB yet
        self.object = form.save(commit=False)
        
        # 2. Assign the current user to the 'created_by' field 
        # (Ensure your model field name is 'created_by')
        self.object.created_by = self.request.user
        
        # 3. Now save to the database
        self.object.save()
        
        # 4. Handle many-to-many fields (like employees) if they exist
        form.save_m2m()

        action = self.request.POST.get('_save_action')
        
        if action == 'add_another':
            messages.success(self.request, "Report saved. Starting a new search.")
            return redirect('daily_reports:create_report')
            
        # Standard Save
        messages.success(self.request, "Report saved successfully.")
        return redirect(self.get_success_url())



# ---------------------------------------------- Update ----------------------------
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import PermissionDenied

class DailyReportUpdateView(LoginRequiredMixin, UpdateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = "daily_reports/dr_update_form.html"
    success_url = reverse_lazy("daily_reports:report_list")

    def dispatch(self, request, *args, **kwargs):
        """
        Enforce the 7-day / same department logic globally for this view.
        """
        report = self.get_object()
        
        is_staff = request.user.is_staff
        is_same_dept = (request.user.department is not None and 
                        request.user.department == report.department)
        is_within_time_limit = (timezone.now() - report.created_at) <= timedelta(days=7)

        # The core permission logic
        if not (is_staff or (is_same_dept and is_within_time_limit)):
            messages.error(request, "You do not have permission to edit this report (limit: 7 days).")
            # Or raise PermissionDenied if you want a 403 page
            return redirect("daily_reports:report_list") 

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['location'] = self.object.location_tag
        
        # Logic for deleting: Staff can always delete, 
        # but regular users might only be allowed if within the same window
        # (Using the same logic as 'can_edit' since this IS the edit page)
        context['can_delete'] = True 
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if hasattr(self.object, 'modified_by'):
            self.object.modified_by = self.request.user
        self.object.save()
        form.save_m2m()
        messages.success(self.request, "Report updated successfully.")
        return redirect(self.get_success_url())
    
    def post(self, request, *args, **kwargs):
        if 'delete_report' in request.POST:
            self.object = self.get_object()
            # Double check permission before actual deletion
            if request.user.is_staff or (request.user.department == self.object.department):
                self.object.delete()
                messages.success(request, "Report deleted successfully.")
                return redirect(self.success_url)
            else:
                messages.error(request, "You are not authorized to delete this report.")
                return redirect(self.success_url)
        return super().post(request, *args, **kwargs)
