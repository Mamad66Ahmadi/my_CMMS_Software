from django import template

register = template.Library()

# Use this to verify the file is actually loading
print("Loading custom template tags...") 

@register.inclusion_tag('work_orders/work_orders_head/components/filter_row.html')
def filter_row(field_config, filters, operators_dict, choices=None):
    return {
        'field': field_config,
        'filters': filters,
        'operators': operators_dict,
        'choices': choices,
    }

@register.filter(name='lookup')
def lookup(dictionary, key):
    """Lookup key in dict."""
    if not isinstance(dictionary, dict):
        return {}
    return dictionary.get(key, {})
