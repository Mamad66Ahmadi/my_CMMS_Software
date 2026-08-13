# equipment/templatetags/to_jalali.py  
from django import template
from django.utils import timezone
import datetime
import jdatetime

register = template.Library()


@register.filter
def to_jalali(value, format_str="%Y/%m/%d %H:%M"):
    """
    Converts a datetime to a Jalali string.
    Usage: {{ permit.valid_from|to_jalali:"%Y/%m/%d %H:%M" }}
    """
    if not value:
        return ""

    try:
        # Handle date-only values (not datetime)
        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            return jdatetime.date.fromgregorian(date=value).strftime(format_str)

        # Normalize aware datetimes to the configured TIME_ZONE so the
        # Jalali output matches the Gregorian output of the |date filter
        if timezone.is_aware(value):
            value = timezone.localtime(value).replace(tzinfo=None)

        j_date = jdatetime.datetime.fromgregorian(datetime=value)
        return j_date.strftime(format_str)
    except (TypeError, ValueError, AttributeError):
        return value
