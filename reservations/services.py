"""Transactional payment and refund services.

Keeping state transitions in one place means the guest checkout, Django admin
actions and the signed gateway webhook all follow the same rules.  Every
function locks the related booking/payment rows before changing state.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import Booking, Payment, PaymentEvent


class PaymentError(Exception):
    """Base class for recoverable payment errors."""


class InvalidTransition(PaymentError):
    """Raised when a payment/booking state change is not allowed."""


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'))


def submit_payment_proof(booking, *, metode_pembayaran, proof=None, actor=None):
    """Attach proof of payment and put the payment into manual verification.

    The amount is always taken from the booking, never from request data.  A
    rejected payment can be retried; a pending or paid payment cannot.
    """
    with transaction.atomic():
        locked_booking = (
            Booking.objects.select_for_update()
            .select_related('room__room_type', 'payment')
            .get(pk=booking.pk)
        )
        if actor is not None and locked_booking.user_id != actor.pk:
            raise PaymentError('Anda tidak berhak mengubah pembayaran reservasi ini.')
        if locked_booking.status_pesanan != 'PENDING_PAYMENT':
            raise InvalidTransition('Reservasi ini tidak lagi menerima pembayaran.')

        payment, _ = Payment.objects.select_for_update().get_or_create(
            booking=locked_booking,
            defaults={
                'amount': locked_booking.total_biaya_akhir,
                'metode_pembayaran': 'Belum dipilih',
                'status_pembayaran': Payment.UNPAID,
            },
        )
        if payment.status_pembayaran in (
            Payment.PENDING_VERIFICATION, Payment.VERIFIED,
            Payment.REFUND_PENDING, Payment.REFUNDED,
        ):
            raise InvalidTransition('Pembayaran ini sedang diproses atau sudah selesai.')

        payment.metode_pembayaran = (metode_pembayaran or '').strip()[:30] or 'Transfer Bank'
        payment.amount = locked_booking.total_biaya_akhir
        if proof is not None:
            payment.bukti_transfer_url = proof
        payment.status_pembayaran = Payment.PENDING_VERIFICATION
        payment.failure_reason = ''
        payment.verified_at = None
        payment.verified_by = None
        payment.save()
        return payment


def verify_payment(payment, *, approved, actor=None, reason=''):
    """Approve or reject a payment and keep the booking status in sync.

    Approving is idempotent, which makes it safe for gateway retries and double
    clicks in the admin.  A cancelled booking can never be re-confirmed by a
    late payment; staff must process a refund instead.
    """
    with transaction.atomic():
        locked_payment = (
            Payment.objects.select_for_update()
            .select_related('booking')
            .get(pk=payment.pk)
        )
        booking = Booking.objects.select_for_update().get(pk=locked_payment.booking_id)

        if approved:
            if locked_payment.status_pembayaran == Payment.VERIFIED:
                return locked_payment
            if locked_payment.status_pembayaran in (
                Payment.REFUND_PENDING, Payment.REFUNDED,
            ):
                raise InvalidTransition('Pembayaran sudah masuk proses refund.')
            if booking.status_pesanan == 'CANCELLED':
                raise InvalidTransition(
                    'Reservasi sudah dibatalkan. Pembayaran tidak dapat dikonfirmasi; '
                    'proses refund sebagai gantinya.'
                )

            locked_payment.status_pembayaran = Payment.VERIFIED
            locked_payment.verified_at = timezone.now()
            locked_payment.verified_by = actor
            locked_payment.failure_reason = ''
            locked_payment.save(update_fields=[
                'status_pembayaran', 'verified_at', 'verified_by',
                'failure_reason', 'updated_at',
            ])

            if booking.status_pesanan == 'PENDING_PAYMENT':
                booking.status_pesanan = 'CONFIRMED'
                booking.save(update_fields=['status_pesanan', 'updated_at'])
            return locked_payment

        # Rejection path
        if locked_payment.status_pembayaran == Payment.REJECTED:
            return locked_payment
        if locked_payment.status_pembayaran in (
            Payment.VERIFIED, Payment.REFUND_PENDING, Payment.REFUNDED,
        ):
            raise InvalidTransition(
                'Pembayaran yang sudah lunas/refund tidak dapat ditolak.'
            )

        locked_payment.status_pembayaran = Payment.REJECTED
        locked_payment.failure_reason = (reason or 'Bukti pembayaran tidak valid.')[:255]
        locked_payment.verified_at = timezone.now()
        locked_payment.verified_by = actor
        locked_payment.save(update_fields=[
            'status_pembayaran', 'failure_reason', 'verified_at',
            'verified_by', 'updated_at',
        ])
        return locked_payment


def request_refund(payment, *, actor=None, reason=''):
    """Mark a verified payment as waiting for a refund."""
    with transaction.atomic():
        locked = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked.status_pembayaran == Payment.REFUND_PENDING:
            return locked
        if locked.status_pembayaran != Payment.VERIFIED:
            raise InvalidTransition('Hanya pembayaran terverifikasi yang dapat direfund.')
        locked.status_pembayaran = Payment.REFUND_PENDING
        locked.refund_requested_at = timezone.now()
        if reason:
            locked.failure_reason = reason[:255]
        if actor is not None:
            locked.verified_by = actor
        locked.save(update_fields=[
            'status_pembayaran', 'refund_requested_at', 'failure_reason',
            'verified_by', 'updated_at',
        ])
        return locked


def complete_refund(payment, *, actor=None, reason=''):
    """Finalise a refund and cancel the booking when the stay has not started."""
    with transaction.atomic():
        locked = (
            Payment.objects.select_for_update()
            .select_related('booking')
            .get(pk=payment.pk)
        )
        if locked.status_pembayaran == Payment.REFUNDED:
            return locked
        if locked.status_pembayaran not in (Payment.VERIFIED, Payment.REFUND_PENDING):
            raise InvalidTransition('Pembayaran ini belum dapat direfund.')

        locked.status_pembayaran = Payment.REFUNDED
        locked.refunded_at = timezone.now()
        if locked.refund_requested_at is None:
            locked.refund_requested_at = timezone.now()
        if actor is not None:
            locked.verified_by = actor
        if reason:
            locked.failure_reason = reason[:255]
        locked.save(update_fields=[
            'status_pembayaran', 'refunded_at', 'refund_requested_at',
            'verified_by', 'failure_reason', 'updated_at',
        ])

        booking = Booking.objects.select_for_update().get(pk=locked.booking_id)
        if booking.status_pesanan in ('PENDING_PAYMENT', 'CONFIRMED'):
            booking.status_pesanan = 'CANCELLED'
            booking.save(update_fields=['status_pesanan', 'updated_at'])
        return locked


def process_gateway_event(*, provider, event_id, event_type, payload):
    """Process one signed gateway event exactly once.

    Returns ``(event, outcome)`` where outcome is ``processed``, ``duplicate``
    or ``ignored``.  Invalid transitions raise ``InvalidTransition`` after the
    error is persisted on the event for staff review.
    """
    event_type = (event_type or '').strip()
    mapping = {
        'payment.paid': 'paid',
        'payment.succeeded': 'paid',
        'payment.failed': 'failed',
        'payment.expired': 'failed',
        'payment.refunded': 'refunded',
    }
    action = mapping.get(event_type)

    with transaction.atomic():
        event, created = PaymentEvent.objects.select_for_update().get_or_create(
            event_id=event_id,
            defaults={
                'provider': provider,
                'event_type': event_type,
                'payload': payload,
            },
        )
        if not created and event.processed_at is not None:
            return event, 'duplicate'
        if not created:
            # Retry of an event that failed previously: refresh the payload.
            event.payload = payload
            event.event_type = event_type
            event.processing_error = ''

        if action is None:
            event.processed_at = timezone.now()
            event.save()
            return event, 'ignored'

        booking_id = payload.get('booking_id') or payload.get('booking')
        try:
            booking = (
                Booking.objects.select_for_update()
                .select_related('room__room_type')
                .get(pk=int(booking_id))
            )
        except (TypeError, ValueError, Booking.DoesNotExist) as exc:
            event.processing_error = 'Booking tidak ditemukan pada payload.'
            event.save()
            raise InvalidTransition('Booking tidak ditemukan pada payload.') from exc

        payment = Payment.objects.select_for_update().filter(booking=booking).first()
        if payment is None:
            payment = booking.ensure_payment()

        raw_amount = payload.get('amount')
        if raw_amount is not None:
            try:
                event_amount = _money(raw_amount)
            except (InvalidOperation, ValueError) as exc:
                event.processing_error = 'Nominal pembayaran tidak valid.'
                event.save()
                raise InvalidTransition('Nominal pembayaran tidak valid.') from exc
            if event_amount != _money(payment.amount):
                event.processing_error = (
                    f'Nominal event {event_amount} tidak sama dengan tagihan {payment.amount}.'
                )
                event.save()
                raise InvalidTransition('Nominal pembayaran tidak sesuai dengan tagihan.')
        elif action == 'paid':
            event.processing_error = 'Payload paid wajib menyertakan amount.'
            event.save()
            raise InvalidTransition('Payload paid wajib menyertakan amount.')

        try:
            if action == 'paid':
                payment = verify_payment(payment, approved=True, reason='Gateway webhook')
            elif action == 'failed':
                if payment.status_pembayaran == Payment.VERIFIED:
                    raise InvalidTransition('Pembayaran sudah lunas; event gagal diabaikan.')
                if payment.status_pembayaran != Payment.REFUNDED:
                    payment.status_pembayaran = Payment.FAILED
                    payment.failure_reason = str(
                        payload.get('reason') or 'Pembayaran gagal di gateway.'
                    )[:255]
                    payment.save(update_fields=[
                        'status_pembayaran', 'failure_reason', 'updated_at',
                    ])
            elif action == 'refunded':
                payment = complete_refund(
                    payment,
                    reason=str(payload.get('reason') or 'Refund dari gateway.'),
                )
        except InvalidTransition as exc:
            event.processing_error = str(exc)
            event.payment = payment
            event.save()
            raise

        event.payment = payment
        event.processed_at = timezone.now()
        event.processing_error = ''
        event.save()
        return event, 'processed'
