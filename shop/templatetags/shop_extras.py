from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    return value * arg

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def to(value, arg):
    """
    Usage: {% for i in 1|to:5 %} → 1,2,3,4,5
    """
    return range(value, arg + 1)

