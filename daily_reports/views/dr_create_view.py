# daily_reports/views/dr_create_views.py 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect


from daily_reports.models import DailyReport
from daily_reports.forms import DailyReportForm


class DailyReportCreateView(LoginRequiredMixin, CreateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = "daily_reports/dr_create_form.html"  # we’ll create this
    success_url = reverse_lazy("daily_reports:report_list")  # adjust to your list view name

    def get_initial(self):
        initial = super().get_initial()
        # Optional: set initial date to today
        # (Model already defaults to today, so this is mostly for form display)
        initial["date"] = timezone.localdate()
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.request.user.department:
            raise PermissionDenied("Your account has no department.")
        
        kwargs['initial'] = kwargs.get('initial', {})
        # Use the ID of the department object
        kwargs['initial']['department'] = self.request.user.department
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Get the action from the POST data
        action = self.request.POST.get('_save_action')
        
        if action == 'add_another':
            messages.success(self.request, "Report saved. You can add another.")
            return redirect('daily_reports:report_create') # Adjust to your URL name
            
        elif action == 'continue':
            messages.success(self.request, "Report saved.")
            return redirect('daily_reports:report_update', pk=self.object.pk) # Adjust to your update URL
            
        else:
            # Default 'save' behavior (go to list)
            return redirect('daily_reports:report_list')