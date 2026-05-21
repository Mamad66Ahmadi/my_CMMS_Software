
from django.db.models import Count, Q, OuterRef, Subquery, IntegerField, Case, When, F
from django.db.models.functions import Coalesce
from datetime import timedelta
from django.utils import timezone

from .models import DailyReport

# ---------------------- Counter Function ----------------------------------------
def annotate_running_counts(queryset):

    today = timezone.now().date()
    thirty_days = timedelta(days=30)
    year_days = timedelta(days=365)

    # ✅ Determine equipment id (same logic as equipment_parent)
    queryset = queryset.annotate(
        equipment_id=Case(
            When(
                location_tag__parent__loc_tag=F("location_tag__unit__unit_code"),
                then=F("location_tag_id"),
            ),
            default=F("location_tag__parent_id"),
            output_field=IntegerField(),
        )
    )

    # ✅ Rolling 365‑day running count for SAME location tag
    year_count_subquery = (
        DailyReport.objects.filter(
            location_tag=OuterRef("location_tag"),
            date__gte=OuterRef("date") - year_days,
            date__lte=OuterRef("date"),
        )
        .filter(
            Q(date__lt=OuterRef("date")) |
            Q(date=OuterRef("date"), id__lte=OuterRef("id"))
        )
        .values("location_tag")
        .annotate(cnt=Count("id"))
        .values("cnt")[:1]
    )

    # ✅ Rolling 30‑day running count for SAME location tag
    month_count_subquery = (
        DailyReport.objects.filter(
            location_tag=OuterRef("location_tag"),
            date__gte=OuterRef("date") - thirty_days,
            date__lte=OuterRef("date"),
        )
        .filter(
            Q(date__lt=OuterRef("date")) |
            Q(date=OuterRef("date"), id__lte=OuterRef("id"))
        )
        .values("location_tag")
        .annotate(cnt=Count("id"))
        .values("cnt")[:1]
    )

    # ✅ Parent equipment running 30‑day count (same running logic)
    parent_count_subquery = (
        DailyReport.objects.annotate(
            equipment_id=Case(
                When(
                    location_tag__parent__loc_tag=F("location_tag__unit__unit_code"),
                    then=F("location_tag_id"),
                ),
                default=F("location_tag__parent_id"),
                output_field=IntegerField(),
            )
        )
        .filter(
            equipment_id=OuterRef("equipment_id"),
            date__gte=OuterRef("date") - thirty_days,
            date__lte=OuterRef("date"),
        )
        .filter(
            Q(date__lt=OuterRef("date")) |
            Q(date=OuterRef("date"), id__lte=OuterRef("id"))
        )
        .values("equipment_id")
        .annotate(total=Count("id"))
        .values("total")[:1]
    )

    return queryset.annotate(
        year_count=Coalesce(Subquery(year_count_subquery, output_field=IntegerField()), 0),
        month_count=Coalesce(Subquery(month_count_subquery, output_field=IntegerField()), 0),
        parent_month_count=Coalesce(Subquery(parent_count_subquery, output_field=IntegerField()), 0),
    )