# equipment/templatetags/top_bar.py
from django import template
from django.utils import timezone
import jdatetime

register = template.Library()

@register.inclusion_tag("top_bar.html", takes_context=True)
def top_bar(context):
    request = context.get("request")
    user = getattr(request, "user", None)

    now = timezone.now()
    jnow = jdatetime.datetime.fromgregorian(datetime=now)

    gregorian_date_str = now.strftime("%Y/%m/%d")
    jalali_date_persian = jnow.strftime("%Y/%m/%d")

    weekday_name = now.strftime("%A")

    # Extract safer values
    username = getattr(user, "username", "Unknown-PC")
    first_name = getattr(user, "first_name", "")
    last_name = getattr(user, "last_name", "")

    # department.name may not exist → avoid errors
    if user and hasattr(user, "department") and user.department:
        department_name = user.department.name
    else:
        department_name = "بدون دپارتمان"

    return {
        "gregorian_date": gregorian_date_str,
        "jalali_date_persian": jalali_date_persian,
        "weekday_name": weekday_name,

        # user info for top_bar.html
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "department_name": department_name,
    }
