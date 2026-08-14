from django import template

register = template.Library()


@register.filter
def padding_range(iterable, minimum=5):
    """Return range(0) if len(iterable) >= minimum, else the shortfall."""
    try:
        length = len(iterable)
    except TypeError:
        length = iterable.count()
    return range(max(0, minimum - length))
