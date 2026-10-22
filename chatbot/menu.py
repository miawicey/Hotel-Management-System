"""Menu browsing helpers shared by the portal view and the concierge."""

from .models import RoomServiceMenuItem


def available_menu():
    """Return the live menu in kitchen display order."""
    return list(
        RoomServiceMenuItem.objects.filter(is_available=True).order_by(
            'category', 'subcategory', 'sort_order', 'name',
        )
    )


def recommended_items(items):
    """Chef's picks, keeping the catalogue's category order."""
    return [item for item in items if item.is_recommended]


def build_menu_groups(items):
    """Group flat menu rows into the portal's category/subcategory shape.

    Result::

        [{'key': 'HEAVY_MEAL', 'label': 'Makanan Berat',
          'description': '...', 'item_count': 17,
          'subgroups': [{'key': 'NASI_GORENG', 'label': 'Nasi Goreng',
                         'items': [...]}, ...]}, ...]
    """
    grouped = {}
    for item in items:
        grouped.setdefault((item.category, item.subcategory), []).append(item)

    groups = []
    for group in RoomServiceMenuItem.MENU_STRUCTURE:
        subgroups = []
        for sub_key, sub_label in group['subcategories']:
            sub_items = grouped.get((group['key'], sub_key), [])
            if sub_items:
                subgroups.append({
                    'key': sub_key,
                    'label': sub_label,
                    'items': sub_items,
                    'item_count': len(sub_items),
                })
        if subgroups:
            groups.append({
                **group,
                'subgroups': subgroups,
                'item_count': sum(sub['item_count'] for sub in subgroups),
            })
    return groups


def menu_stats(items):
    """Small numbers used by the portal hero and the AI context."""
    return {
        'total': len(items),
        'recommended': len(recommended_items(items)),
        'available': sum(1 for item in items if item.is_available),
    }
