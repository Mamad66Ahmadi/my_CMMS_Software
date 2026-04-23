from django import template

register = template.Library()

@register.inclusion_tag("sidebar.html")
def render_sidebar():
    # You can add logic here (e.g., if user is admin, show extra links)
    return {}
