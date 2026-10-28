from django import template

register = template.Library()

@register.filter
def get_item(mapping, key):
    """{{ some_dict|get_item:key }} - lookup dict yang aman di template."""
    try:
        return mapping.get(key, "")
    except AttributeError:
        return ""