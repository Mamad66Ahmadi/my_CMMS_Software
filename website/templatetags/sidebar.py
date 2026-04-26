from django import template

register = template.Library()

@register.inclusion_tag("sidebar.html", takes_context=True)
def render_sidebar(context):
    # You can add logic here (e.g., if user is admin, show extra links)
    return context
