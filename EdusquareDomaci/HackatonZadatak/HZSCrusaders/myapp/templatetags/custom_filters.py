from django import template

register = template.Library()

@register.filter
def make_range(value):
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def first_letter(value):
    try:
        return value[0]
    except (IndexError, TypeError):
        return ''