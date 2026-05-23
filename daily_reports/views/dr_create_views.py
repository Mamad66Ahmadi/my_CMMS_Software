from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, View
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from daily_reports.models import DailyReport
from daily_reports.forms import DailyReportForm
from equipment.models.equipment_models import LocationTag



from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.http import JsonResponse
from django.template.loader import render_to_string

from daily_reports.models import DailyReport
from daily_reports.forms import DailyReportForm
from equipment.models.equipment_models import LocationTag


class ReportCreateView(LoginRequiredMixin, CreateView):
    model = DailyReport
    form_class = DailyReportForm
    template_name = "daily_reports/dr_form_step2.html"
    success_url = reverse_lazy("daily_reports:report_list")

    def is_ajax(self):
        return (
            self.request.headers.get("x-requested-with") == "XMLHttpRequest"
            or self.request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
        )

    def get_location_id(self):
        return (
            self.request.POST.get("location_tag")   # hidden form field
            or self.request.GET.get("location_id")  # when loading step2
        )

    def get_location_obj(self):
        loc_id = self.get_location_id()
        if not loc_id:
            return None
        try:
            return LocationTag.objects.get(id=loc_id)
        except LocationTag.DoesNotExist:
            return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request

        # Pre-fill location_tag from ?location_id=...
        loc_id = self.request.GET.get("location_id")
        if loc_id:
            initial = kwargs.get("initial", {})
            initial["location_tag"] = loc_id
            kwargs["initial"] = initial

        return kwargs

    def render_form_html(self, form):
        location = self.get_location_obj()
        context = {
            "form": form,
            "location_tag": location.loc_tag if location else "",
            "location": location,
        }
        return render_to_string(self.template_name, context, request=self.request)

    def form_valid(self, form):
        self.object = form.save()
        if self.is_ajax():
            return JsonResponse({"success": True})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({"success": False, "html": self.render_form_html(form)})
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location = self.get_location_obj()
        context["location_tag"] = location.loc_tag if location else ""
        return context



class RecentReportsPartialView(LoginRequiredMixin, View):
    """View to fetch the list of recent reports for the modal."""
    def get(self, request):
        location_id = request.GET.get('location_id')
        location = get_object_or_404(LocationTag, id=location_id)
        
        reports = DailyReport.objects.filter(
            location_tag_id=location_id,
            department=request.user.department 
        ).order_by('-date')[:5]

        return render(request, 'daily_reports/dr_recent_reports.html', {
            'reports': reports,
            'location_tag': location.loc_tag
        })


class ReportDetailJsonView(LoginRequiredMixin, View):
    """View to fetch specific report data for form auto-population."""
    def get(self, request, pk):
        report = get_object_or_404(DailyReport, pk=pk)
        
        # Since employees is a CharField, it is already a string.
        # We just pass it as is (or handle as an empty string if None).
        employees_data = report.employees if report.employees is not None else ""
            
        data = {
            'actual_start': report.actual_start.strftime('%Y-%m-%d') if report.actual_start else '',
            'wo_number': report.wo_number,
            'department_id': report.department_id,
            'employees': employees_data
        }
        return JsonResponse(data)



from django.views.generic import TemplateView

class DailyReportPortalView(LoginRequiredMixin, TemplateView):
    template_name = 'daily_reports/test.html'