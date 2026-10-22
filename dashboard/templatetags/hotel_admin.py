"""Template tags that add hotel operations context to the Django admin."""

from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def admin_metrics():
    """Return operational review queues shown on the admin index page.

    Imports are lazy and the whole lookup is guarded: a half-migrated or
    empty database must never break the admin dashboard.
    """
    try:
        from chatbot.models import ServiceOrder
        from reservations.models import Booking, Payment

        return [
            {
                'label': 'Menunggu pembayaran',
                'value': Booking.objects.filter(
                    status_pesanan='PENDING_PAYMENT',
                ).count(),
                'hint': 'Booking belum dibayar',
                'url': (
                    reverse('admin:reservations_booking_changelist')
                    + '?status_pesanan=PENDING_PAYMENT'
                ),
            },
            {
                'label': 'Bukti menunggu verifikasi',
                'value': Payment.objects.filter(
                    status_pembayaran=Payment.PENDING_VERIFICATION,
                ).count(),
                'hint': 'Setujui atau tolak bukti transfer',
                'url': (
                    reverse('admin:reservations_payment_changelist')
                    + f'?status_pembayaran={Payment.PENDING_VERIFICATION}'
                ),
            },
            {
                'label': 'Refund berjalan',
                'value': Payment.objects.filter(
                    status_pembayaran__in=(
                        Payment.REFUND_PENDING, Payment.REFUNDED,
                    ),
                ).count(),
                'hint': 'Pengembalian dana tamu',
                'url': (
                    reverse('admin:reservations_payment_changelist')
                    + f'?status_pembayaran={Payment.REFUND_PENDING}'
                ),
            },
            {
                'label': 'Pesanan room service aktif',
                'value': ServiceOrder.objects.filter(
                    status__in=('PENDING', 'CONFIRMED'),
                ).count(),
                'hint': 'Antrian dapur & layanan kamar',
                'url': (
                    reverse('admin:chatbot_serviceorder_changelist')
                    + '?status=PENDING'
                ),
            },
        ]
    except Exception:  # pragma: no cover - defensive for admin safety
        return []
