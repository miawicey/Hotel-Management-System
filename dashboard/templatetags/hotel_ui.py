"""Presentation filters shared by the guest-facing templates."""

from django import template

register = template.Library()


@register.filter
def rupiah(value):
    """Format a number the Indonesian way: 5610000 → '5.610.000'.

    Values that are not numbers are returned untouched so a partially filled
    context can never break a page.
    """
    try:
        amount = round(float(value))
    except (TypeError, ValueError):
        return value
    return f'{amount:,.0f}'.replace(',', '.')
