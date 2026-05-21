from django import template
import jdatetime

register = template.Library()

@register.filter
def to_jalali(value):
    if not value:
        return ""
    jdate = jdatetime.date.fromgregorian(date=value)
    return jdate.strftime("%Y-%m-%d")
