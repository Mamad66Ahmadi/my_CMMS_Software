# daily_reports/views/dr_create_views.py

from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from daily_reports.models import DailyReport
from daily_reports.forms import DailyReportForm  

# daily_reports/views/dr_create_views.py
class ReportCreateView(LoginRequiredMixin, CreateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = 'daily_reports/dr_form.html'
    success_url = reverse_lazy('daily_reports:report_list')

    def get_form_kwargs(self):
        """Pass the request to the form so we can access the user."""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # No need to manually set department here anymore, 
        # as the form will provide the value chosen by the user.
        return super().form_valid(form)

from django.shortcuts import render

def test_autocomplete_view(request):
    return render(request, 'daily_reports/test_autocomplete.html')


