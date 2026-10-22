from django import template

register = template.Library()


@register.filter
def quantity_field(form, item_id):
    """Return the bound quantity field for a menu item id."""
    try:
        return form[f'quantity_{item_id}']
    except (KeyError, TypeError):
        return ''


@register.filter
def status_tone(order):
    return getattr(order, 'status_tone', 'pending')


@register.filter
def concat(value, suffix):
    return f'{value}{suffix}'
