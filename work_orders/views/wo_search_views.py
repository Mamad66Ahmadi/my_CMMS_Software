# work_orders/views/wo_search_views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView

# Import config and services
from work_orders.services.wo_filter_config import *
from work_orders.services.wo_filter_choices import build_filter_choices_map
from work_orders.services.wo_filter_service import get_filtered_work_orders
from work_orders.services.wo_sorting import WORK_ORDER_LIST_SORT_FIELDS, get_sort_field

class WorkOrderSearchView(LoginRequiredMixin, TemplateView):
    template_name = "work_orders/work_orders_head/wo_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # Build structured_filters for nested lookup in template tag
        structured_filters = {
            field['name']: {
                'op1':  request.GET.get(f"{field['name']}_op1",  ""),
                'val1': request.GET.get(f"{field['name']}_val1", ""),
                'op2':  request.GET.get(f"{field['name']}_op2",  ""),
                'val2': request.GET.get(f"{field['name']}_val2", ""),
            }
            for field in FIELD_CONFIGS
        }

        context.update({
            'field_configs':      FIELD_CONFIGS,
            'structured_filters': structured_filters,
            'choices_map':        build_filter_choices_map(), # Use the new service
            'operators_map':      { # Keep this inline or move to config if it gets large
                'numeric': NUMERIC_OPERATORS,
                'dropdown': DROPDOWN_OPERATORS,
                'text': TEXT_OPERATORS,
            },
            'per_page':           request.GET.get('per_page', '25'),
        })
        return context


class WorkOrderList(LoginRequiredMixin, TemplateView):
    template_name = "work_orders/work_orders_head/wo_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # Check if any real filter exists
        if not _has_any_filter(request):
            context.update({
                "work_orders": None,
                "error_message": "Please select at least one filter."
            })
            return context

        queryset, filters = get_filtered_work_orders(request)

        sort_by_param = request.GET.get("sort", "-reported_at")
        sort_field = get_sort_field(sort_by_param, WORK_ORDER_LIST_SORT_FIELDS)

        queryset = queryset.order_by(sort_field, "-id")

        try:
            per_page = int(request.GET.get("per_page", 25))
        except ValueError:
            per_page = 25

        if per_page not in [10, 25, 50, 100]:
            per_page = 25

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(request.GET.get("page"))

        query_dict = request.GET.copy()
        query_dict.pop("sort", None)
        query_dict.pop("page", None)

        context.update({
            "work_orders": page_obj,
            "filters": filters,
            "sort_by": sort_by_param,
            "per_page": per_page,
            "query_params": query_dict.urlencode(),
        })

        return context

def _has_any_filter(request):
    for field in FIELD_CONFIGS:
        if request.GET.get(f"{field['name']}_val1") or request.GET.get(f"{field['name']}_val2"):
            return True
    return False
