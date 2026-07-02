# work_orders/templatetags/wo_sort_tags.py

from django import template

register = template.Library()


@register.filter
def split(value, separator=","):
    """
    Split string into list.

    Example:
        "a,b,c"|split:","
    """
    if not value:
        return []

    return value.split(separator)


@register.simple_tag
def sort_priority(sort_by, column):
    """
    Returns the 1-based sort priority for a column.

    Example:
        sort_by="status,-priority,wo_number"

        status      -> 1
        priority    -> 2
        wo_number   -> 3
    """

    if not sort_by:
        return ""

    sort_list = [item.strip() for item in sort_by.split(",") if item.strip()]

    for index, item in enumerate(sort_list, start=1):
        if item.lstrip("-") == column:
            return index

    return ""


@register.simple_tag
def next_sort_value(sort_by, column):
    """
    Builds next multi-sort string when user clicks a column.

    Behavior:
    - unsorted column -> add ascending to front
    - ascending column -> toggle to descending
    - descending column -> toggle to ascending

    Examples:

        current:
            status,-priority

        click priority:
            priority,status

        click status:
            -status,-priority
    """

    current = []

    if sort_by:
        current = [
            item.strip()
            for item in sort_by.split(",")
            if item.strip()
        ]

    asc = column
    desc = f"-{column}"

    # detect current state
    is_asc = asc in current
    is_desc = desc in current

    # remove existing version
    current = [
        item for item in current
        if item not in [asc, desc]
    ]

    # toggle
    if is_asc:
        current.insert(0, desc)

    elif is_desc:
        current.insert(0, asc)

    else:
        current.insert(0, asc)

    return ",".join(current)
