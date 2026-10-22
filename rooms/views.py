from datetime import timedelta

from django.db.models import Avg, Count
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date

from reservations.models import Booking, Review
from .models import Room, RoomType

# Editorial photography per room family — keeps the listing visually varied
# while every card keeps the same frame, ratio, and overlay treatment.
ROOM_IMAGES = {
    'villa': 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1400&q=85',
    'suite': 'https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1400&q=85',
    'twin': 'https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1400&q=85',
    'king': 'https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1400&q=85',
}
DEFAULT_ROOM_IMAGE = (
    'https://images.unsplash.com/photo-1566665797739-1674de7a421a'
    '?auto=format&fit=crop&w=1400&q=85'
)


def _room_image(room_type_name):
    lowered = room_type_name.lower()
    for keyword, url in ROOM_IMAGES.items():
        if keyword in lowered:
            return url
    return DEFAULT_ROOM_IMAGE


def _room_card(room):
    price = f'{room.room_type.price_per_night:,.0f}'.replace(',', '.')
    return {
        'id': room.pk,
        'number': room.number,
        'name': f'Kamar {room.number}',
        'type_name': room.room_type.name,
        'label': f'Lantai {room.floor} · {room.room_type.name}',
        'floor': room.floor,
        'price': price,
        'price_value': int(room.room_type.price_per_night),
        'total': price,
        'capacity_value': room.room_type.capacity,
        'size': f'Kapasitas {room.room_type.capacity} tamu',
        'bed': 'Tempat tidur sesuai tipe kamar',
        'capacity': f'Maks {room.room_type.capacity} tamu',
        'view': 'Pemandangan hotel',
        'badge': 'Tersedia' if room.status == 'CLEAN' else room.get_status_display(),
        'is_available': room.status == 'CLEAN',
        'description': room.room_type.description,
        'image': _room_image(room.room_type.name),
        'features': ['Wi-Fi berkecepatan tinggi', 'Layanan kamar 24 jam', 'Sarapan untuk dua tamu'],
    }


def room_list(request):
    room_types = RoomType.objects.all()
    rooms = Room.objects.filter(is_active=True).select_related('room_type')

    selected_type = request.GET.get('type')
    if selected_type:
        rooms = rooms.filter(room_type_id=selected_type)

    selected_status = request.GET.get('status')
    if selected_status:
        rooms = rooms.filter(status=selected_status)

    guests = request.GET.get('guests', '')
    if guests.isdigit():
        rooms = rooms.filter(room_type__capacity__gte=int(guests))

    check_in_raw = request.GET.get('check_in', '')
    check_out_raw = request.GET.get('check_out', '')
    check_in = parse_date(check_in_raw) if check_in_raw else None
    check_out = parse_date(check_out_raw) if check_out_raw else None

    availability_error = ''
    availability_checked = bool(check_in and check_out)
    if availability_checked:
        if check_out <= check_in:
            availability_error = 'Tanggal check-out harus setelah check-in.'
            rooms = rooms.none()
        else:
            available_ids = Booking.available_rooms(check_in, check_out).values('pk')
            rooms = rooms.filter(pk__in=available_ids)

    rooms = rooms.exclude(status='MAINTENANCE')
    room_cards = [_room_card(room) for room in rooms]

    context = {
        'rooms': room_cards,
        'room_count': len(room_cards),
        'availability_checked': availability_checked,
        'availability_error': availability_error,
        'room_types': room_types,
        'selected_type': selected_type,
        'selected_status': selected_status,
        'check_in': check_in_raw,
        'check_out': check_out_raw,
        'guests': guests,
    }
    return render(request, 'rooms/room_list.html', context)


def room_detail(request, pk):
    room = get_object_or_404(
        Room.objects.select_related('room_type'), pk=pk, is_active=True
    )

    today = timezone.localdate()
    end = today + timedelta(days=14)
    blocked = {
        a.date: a
        for a in room.availabilities.filter(
            date__gte=today, date__lt=end, is_available=False
        )
    }

    blocking_statuses = ['PENDING_PAYMENT', 'CONFIRMED', 'CHECKED_IN']
    booked_dates = set()
    for check_in, check_out in room.bookings.filter(
        status_pesanan__in=blocking_statuses,
        tanggal_check_out__gt=today,
        tanggal_check_in__lt=end,
    ).values_list('tanggal_check_in', 'tanggal_check_out'):
        cursor = max(check_in, today)
        while cursor < check_out and cursor < end:
            booked_dates.add(cursor)
            cursor += timedelta(days=1)

    calendar = []
    for i in range(14):
        d = today + timedelta(days=i)
        entry = blocked.get(d)
        is_booked = d in booked_dates
        calendar.append({
            'date': d,
            'available': entry is None and not is_booked,
            'note': entry.note if entry else ('Terisi' if is_booked else ''),
        })

    reviews = (
        Review.objects.filter(booking__room=room)
        .select_related('guest')
        .order_by('-created_at')
    )
    rating_summary = reviews.aggregate(average=Avg('rating'), count=Count('id'))

    return render(request, 'rooms/room_detail.html', {
        'room': _room_card(room),
        'calendar': calendar,
        'reviews': reviews[:4],
        'rating_average': rating_summary['average'],
        'rating_round': round(rating_summary['average'] or 0),
        'rating_count': rating_summary['count'],
    })


def _rating_distribution(reviews):
    """Five rows (5★ → 1★) with counts and percentages for the rating bars."""
    total = reviews.count()
    # ``order_by()`` clears any ordering: a lingering ORDER BY would leak into
    # the GROUP BY and turn every bucket into a count of one.
    counts = dict(
        reviews.order_by()
        .values_list('rating')
        .annotate(c=Count('id'))
        .values_list('rating', 'c')
    )
    distribution = []
    for value in range(5, 0, -1):
        count = counts.get(value, 0)
        distribution.append({
            'stars': value,
            'count': count,
            'percent': round(count * 100 / total) if total else 0,
        })
    return distribution


def review_list(request):
    """Guest review wall ("Ulasan Tamu") with filters and rating distribution."""
    reviews = (
        Review.objects.select_related('guest', 'booking__room__room_type')
        .order_by('-created_at')
    )
    summary = reviews.aggregate(average=Avg('rating'), count=Count('id'))

    distribution = _rating_distribution(reviews)

    selected_rating = request.GET.get('rating', '')
    if not (selected_rating.isdigit() and 1 <= int(selected_rating) <= 5):
        selected_rating = ''
    if selected_rating:
        reviews = reviews.filter(rating=int(selected_rating))

    # Nudge signed-in guests who have stayed but not reviewed yet.
    pending_reviews = []
    if request.user.is_authenticated:
        pending_reviews = list(
            Booking.objects.filter(
                user=request.user,
                status_pesanan='CHECKED_OUT',
                review__isnull=True,
            ).select_related('room__room_type')[:3]
        )

    return render(request, 'rooms/review_list.html', {
        'reviews': reviews,
        'rating_average': summary['average'],
        'rating_round': round(summary['average'] or 0),
        'rating_count': summary['count'],
        'distribution': distribution,
        'selected_rating': selected_rating,
        'pending_reviews': pending_reviews,
    })
