"""Domain models for bookings, payments, vouchers and guest reviews.

The payment lifecycle is intentionally explicit.  A booking is never marked
CONFIRMED until a payment has been verified (manually by staff or through a
signed gateway webhook).  All amount calculations live on the models so views,
admin actions and webhook handlers share exactly the same rules.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone
<<<<<<< HEAD

from rooms.models import Room, RoomAvailability

=======

from rooms.models import Room, RoomAvailability
from core.models import TimeStampedModel

>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63

MONEY_PRECISION = Decimal('0.01')
TAX_RATE = Decimal('0.11')


def _money(value) -> Decimal:
    """Round a monetary value consistently across the application."""
    return Decimal(str(value)).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


<<<<<<< HEAD
class BaseTransaction(models.Model):
    """Common timestamps shared by the transaction models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
=======
class BaseTransaction(TimeStampedModel):
    """Common timestamps shared by the transaction models.
    
    Inherits from core.models.TimeStampedModel (Abstract Base Class).
    Demonstrates inheritance: BaseTransaction is-a TimeStampedModel.
    """
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63

    class Meta:
        abstract = True


class PromoVoucher(BaseTransaction):
    """Voucher promo dengan kuota terbatas.
    
    Encapsulation: kuota penggunaan dilindungi dengan method protected
    agar hanya bisa dikonsumsi melalui jalur yang terkontrol.
    """
    kode_voucher = models.CharField(max_length=50, unique=True)
    persen_diskon = models.FloatField(default=0.0)
    potongan_nominal = models.FloatField(default=0.0)
    minimal_transaksi = models.FloatField(default=0.0)
    tanggal_kedaluwarsa = models.DateTimeField()
    kuota_penggunaan = models.IntegerField(default=0)

    def is_valid(self, total_transaksi):
        """Public method: mengecek validitas voucher."""
        return (
            self.kuota_penggunaan > 0
            and timezone.now() <= self.tanggal_kedaluwarsa
            and Decimal(str(total_transaksi)) >= Decimal(str(self.minimal_transaksi))
        )

    def _consume_quota(self, jumlah=1):
        """Protected method: konsumsi kuota voucher.
        Hanya boleh dipanggil dari dalam class/service terkait.
        """
        if jumlah <= 0:
            raise ValidationError("Jumlah konsumsi kuota tidak valid.")
        if self.kuota_penggunaan < jumlah:
            raise ValidationError("Kuota voucher tidak mencukupi.")
        self.kuota_penggunaan -= jumlah
        self.save(update_fields=['kuota_penggunaan', 'updated_at'])
        return True

    def _return_quota(self, jumlah=1):
        """Protected method: mengembalikan kuota voucher saat pembatalan."""
        if jumlah <= 0:
            raise ValidationError("Jumlah pengembalian kuota tidak valid.")
        self.kuota_penggunaan += jumlah
        self.save(update_fields=['kuota_penggunaan', 'updated_at'])
        return True

    def __str__(self):
        return self.kode_voucher


class Booking(BaseTransaction):
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CHECKED_IN', 'Checked-in'),
        ('CHECKED_OUT', 'Checked-out'),
        ('CANCELLED', 'Dibatalkan'),
    ]
    # A booking in one of these states still holds the room.
    BLOCKING_STATUSES = ('PENDING_PAYMENT', 'CONFIRMED', 'CHECKED_IN')
    SERVICE_ELIGIBLE_STATUSES = ('PENDING_PAYMENT', 'CONFIRMED', 'CHECKED_IN')

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='guest_id',
        related_name='bookings',
    )
    room = models.ForeignKey(
        Room, on_delete=models.PROTECT, db_column='room_id',
        related_name='bookings',
    )
    voucher = models.ForeignKey(
        PromoVoucher, on_delete=models.SET_NULL, null=True, blank=True,
    )

    tanggal_check_in = models.DateField(db_column='check_in_date')
    tanggal_check_out = models.DateField(db_column='check_out_date')
    jumlah_tamu = models.PositiveIntegerField(default=1, db_column='guest_count')

    total_harga_dasar = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, db_column='total_amount',
    )
    diskon_voucher = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Nilai diskon voucher yang benar-benar diterapkan.',
    )
    pajak_dan_layanan = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    total_biaya_akhir = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    status_pesanan = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='PENDING_PAYMENT',
        db_column='status',
    )
    # Menandai bahwa kuota voucher sudah dikonsumsi sehingga bisa
    # dikembalikan secara aman saat booking dibatalkan.
    voucher_digunakan = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tanggal_check_out__gt=models.F('tanggal_check_in')),
                name='booking_checkout_after_checkin',
            ),
            models.CheckConstraint(
                condition=models.Q(jumlah_tamu__gt=0),
                name='booking_guest_count_positive',
            ),
        ]

    # ------------------------------------------------------------------
    # Authorization / presentation helpers
    # ------------------------------------------------------------------
    def __str__(self):
        return f'{self.booking_code} - {self.room}'

    @property
    def booking_code(self):
        """Human friendly reservation code used across the guest portal."""
        return f'NH-{self.pk:04d}' if self.pk else 'NH-'

    @property
    def durasi_malam(self):
        if not self.tanggal_check_in or not self.tanggal_check_out:
            return 1
        return max((self.tanggal_check_out - self.tanggal_check_in).days, 1)

    @property
    def subtotal_setelah_diskon(self):
        return max(Decimal('0'), self.total_harga_dasar - self.diskon_voucher)

    @property
    def payment_record(self):
        """Return the related payment or None without raising an exception."""
        try:
            return self.payment
        except Payment.DoesNotExist:
            return None

    @property
    def payment_status_group(self):
        """Normalised status used by badges: pending/paid/failed/refund/cancelled."""
        payment = self.payment_record
        if payment is None:
            return 'pending'
        if payment.status_pembayaran == 'VERIFIED':
            return 'paid'
        if payment.status_pembayaran in ('REFUND_PENDING', 'REFUNDED'):
            return 'refund'
        if payment.status_pembayaran in ('REJECTED', 'FAILED'):
            return 'failed'
        if self.status_pesanan == 'CANCELLED':
            return 'cancelled'
        return 'pending'

    @property
    def payment_status_label(self):
        payment = self.payment_record
        if payment is None:
            return 'Belum ada tagihan'
        if self.status_pesanan == 'CANCELLED' and payment.status_pembayaran == 'UNPAID':
            return 'Dibatalkan'
        return payment.get_status_pembayaran_display()

    @property
    def can_cancel(self):
        return self.status_pesanan in ('PENDING_PAYMENT', 'CONFIRMED')

    @property
    def can_order_room_service(self):
        """True for stays that are currently active or still upcoming."""
        return (
            self.status_pesanan in self.SERVICE_ELIGIBLE_STATUSES
            and self.tanggal_check_out >= timezone.localdate()
        )

    @property
    def review_allowed(self):
        return self.status_pesanan == 'CHECKED_OUT' and not hasattr(self, 'review')

    # ------------------------------------------------------------------
    # Availability / pricing
    # ------------------------------------------------------------------
    @classmethod
    def available_rooms(cls, check_in, check_out):
        if check_out <= check_in:
            raise ValueError('Tanggal check-out harus setelah check-in.')

        blocked_room_ids = cls.objects.filter(
            status_pesanan__in=cls.BLOCKING_STATUSES,
            tanggal_check_in__lt=check_out,
            tanggal_check_out__gt=check_in,
        ).values('room_id')
        blocked_dates = RoomAvailability.objects.filter(
            date__gte=check_in,
            date__lt=check_out,
            is_available=False,
        ).values('room_id')
        return Room.objects.filter(is_active=True, status='CLEAN').exclude(
            pk__in=blocked_room_ids,
        ).exclude(pk__in=blocked_dates)

    def hitung_total_biaya(self):
        """Calculate the room subtotal, voucher discount, tax and grand total."""
        self.total_harga_dasar = _money(
            Decimal(str(self.room.room_type.price_per_night)) * self.durasi_malam
        )
        diskon = Decimal('0')
        self._voucher_applied = False

        if self.voucher_id and self.voucher and self.voucher.is_valid(self.total_harga_dasar):
            if self.voucher.persen_diskon > 0:
                diskon = (
                    self.total_harga_dasar
                    * Decimal(str(self.voucher.persen_diskon))
                    / Decimal('100')
                )
            else:
                diskon = Decimal(str(self.voucher.potongan_nominal))
            diskon = min(max(diskon, Decimal('0')), self.total_harga_dasar)
            self._voucher_applied = diskon > 0

        self.diskon_voucher = _money(diskon)
        subtotal = self.subtotal_setelah_diskon
        self.pajak_dan_layanan = _money(subtotal * TAX_RATE)
        self.total_biaya_akhir = _money(subtotal + self.pajak_dan_layanan)
        self.save(update_fields=[
            'total_harga_dasar', 'diskon_voucher', 'pajak_dan_layanan',
            'total_biaya_akhir', 'updated_at',
        ])
        return self.total_biaya_akhir

    @transaction.atomic
    def konsumsi_voucher(self):
<<<<<<< HEAD
        """Consume one voucher quota unit, raising if the quota ran out meanwhile."""
=======
        """Consume one voucher quota unit, raising if the quota ran out meanwhile.
        Encapsulation: menggunakan method protected _consume_quota() pada PromoVoucher.
        """
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
        if not getattr(self, '_voucher_applied', False) or not self.voucher_id:
            return False
        voucher = PromoVoucher.objects.select_for_update().get(pk=self.voucher_id)
        if voucher.kuota_penggunaan <= 0:
            raise ValidationError(
                'Kuota voucher sudah habis. Silakan pilih voucher lain atau lanjutkan tanpa voucher.'
            )
<<<<<<< HEAD
        voucher.kuota_penggunaan -= 1
        voucher.save(update_fields=['kuota_penggunaan', 'updated_at'])
=======
        voucher._consume_quota(1)  # Menggunakan method protected untuk kontrol akses
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
        self.voucher_digunakan = True
        self.save(update_fields=['voucher_digunakan', 'updated_at'])
        return True

    @transaction.atomic
    def _kembalikan_voucher(self):
<<<<<<< HEAD
        if not self.voucher_digunakan or not self.voucher_id:
            return False
        voucher = PromoVoucher.objects.select_for_update().get(pk=self.voucher_id)
        voucher.kuota_penggunaan += 1
        voucher.save(update_fields=['kuota_penggunaan', 'updated_at'])
=======
        """Mengembalikan kuota voucher saat booking dibatalkan.
        Menggunakan method protected _return_quota() untuk enkapsulasi.
        """
        if not self.voucher_digunakan or not self.voucher_id:
            return False
        voucher = PromoVoucher.objects.select_for_update().get(pk=self.voucher_id)
        voucher._return_quota(1)  # Menggunakan method protected
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
        self.voucher_digunakan = False
        self.save(update_fields=['voucher_digunakan', 'updated_at'])
        return True

    # ------------------------------------------------------------------
    # Payment / stay lifecycle
    # ------------------------------------------------------------------
    def ensure_payment(self):
        """Create the single payment record every booking must have."""
        payment, created = Payment.objects.get_or_create(
            booking=self,
            defaults={
                'amount': self.total_biaya_akhir,
                'metode_pembayaran': 'Belum dipilih',
                'status_pembayaran': 'UNPAID',
            },
        )
        if (
            not created
            and payment.status_pembayaran in ('UNPAID', 'REJECTED', 'FAILED')
            and payment.amount != self.total_biaya_akhir
        ):
            payment.amount = self.total_biaya_akhir
            payment.save(update_fields=['amount', 'updated_at'])
        return payment

    def konfirmasi(self):
        """Confirm a booking only when its payment is verified.

        Prefer :func:`reservations.services.verify_payment` for state changes;
        this method remains as a safe fallback for legacy callers.
        """
        payment = self.payment_record
        if payment is None or payment.status_pembayaran != 'VERIFIED':
            return False
        if self.status_pesanan != 'PENDING_PAYMENT':
            return self.status_pesanan == 'CONFIRMED'
        self.status_pesanan = 'CONFIRMED'
        self.save(update_fields=['status_pesanan', 'updated_at'])
        return True

    @transaction.atomic
    def batalkan_pesanan(self):
        """Cancel a pending/confirmed booking and release its voucher quota.

        A verified payment is moved to REFUND_PENDING so staff can settle the
        refund explicitly instead of the booking silently keeping a paid state.
        """
        booking = (
            Booking.objects.select_for_update()
            .select_related('payment')
            .get(pk=self.pk)
        )
        if not booking.can_cancel:
            return False

        booking._kembalikan_voucher()
        booking.status_pesanan = 'CANCELLED'
        booking.save(update_fields=['status_pesanan', 'updated_at'])

        payment = booking.payment_record
        if payment is not None and payment.status_pembayaran == 'VERIFIED':
            payment.mark_refund_pending(reason='Booking dibatalkan oleh tamu.')

        self.refresh_from_db()
        return True

    def check_in(self):
        if self.status_pesanan != 'CONFIRMED':
            return False
        self.status_pesanan = 'CHECKED_IN'
        self.checked_in_at = timezone.now()
        self.save(update_fields=['status_pesanan', 'checked_in_at', 'updated_at'])
        return True

    def check_out(self):
        if self.status_pesanan != 'CHECKED_IN':
            return False
        self.status_pesanan = 'CHECKED_OUT'
        self.checked_out_at = timezone.now()
        self.save(update_fields=['status_pesanan', 'checked_out_at', 'updated_at'])
        self.room.status = 'DIRTY'
        self.room.save(update_fields=['status'])
        return True


class Payment(BaseTransaction):
    """Payment attached one-to-one to a booking.

    Status flow (manual transfer):
        UNPAID -> PENDING_VERIFICATION -> VERIFIED
                                      -> REJECTED -> (retry) PENDING_VERIFICATION
        VERIFIED -> REFUND_PENDING -> REFUNDED

    Gateway-driven payments can also move UNPAID -> VERIFIED or FAILED through
    the signed webhook endpoint.  Invalid transitions are rejected by the
    service layer.
<<<<<<< HEAD
=======
    
    Encapsulation: Status perubahan pembayaran dikendalikan melalui
    reservations.services (single gate) untuk menjaga validitas transaksi.
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
    """

    UNPAID = 'UNPAID'
    PENDING_VERIFICATION = 'PENDING_VERIFICATION'
    VERIFIED = 'VERIFIED'
    REJECTED = 'REJECTED'
    FAILED = 'FAILED'
    REFUND_PENDING = 'REFUND_PENDING'
    REFUNDED = 'REFUNDED'

    STATUS_PAYMENT = [
        (UNPAID, 'Menunggu Pembayaran'),
        (PENDING_VERIFICATION, 'Menunggu Verifikasi'),
        (VERIFIED, 'Lunas / Terverifikasi'),
        (REJECTED, 'Ditolak'),
        (FAILED, 'Gagal'),
        (REFUND_PENDING, 'Refund Diproses'),
        (REFUNDED, 'Refunded'),
    ]

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name='payment',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metode_pembayaran = models.CharField(max_length=30, db_column='method')
    bukti_transfer_url = models.ImageField(
        upload_to='bukti_transfer/', null=True, blank=True, db_column='proof',
    )
    status_pembayaran = models.CharField(
        max_length=30, choices=STATUS_PAYMENT, default=UNPAID, db_column='status',
    )
    failure_reason = models.CharField(max_length=255, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_payments',
    )
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment {self.booking.booking_code} ({self.get_status_pembayaran_display()})'

    @property
    def status_group(self):
        if self.status_pembayaran == self.VERIFIED:
            return 'paid'
        if self.status_pembayaran in (self.REFUND_PENDING, self.REFUNDED):
            return 'refund'
        if self.status_pembayaran in (self.REJECTED, self.FAILED):
            return 'failed'
        return 'pending'

    @property
    def is_paid(self):
        return self.status_pembayaran == self.VERIFIED

    @property
    def can_retry(self):
        return (
            self.status_pembayaran in (self.UNPAID, self.REJECTED, self.FAILED)
            and self.booking.status_pesanan == 'PENDING_PAYMENT'
        )

<<<<<<< HEAD
=======
    # Encapsulation helpers
    def __is_verifiable(self):
        """Private method: hanya bisa diakses dari dalam class ini."""
        return self.status_pembayaran in (self.PENDING_VERIFICATION, self.REJECTED)

    @property
    def is_refundable(self):
        """Public property: cek apakah bisa direfund."""
        return self.status_pembayaran == self.VERIFIED

    @property
    def is_in_process(self):
        """Public property: cek apakah pembayaran sedang diproses."""
        return self.status_pembayaran in (
            self.PENDING_VERIFICATION, self.REFUND_PENDING
        )

>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
    # Thin wrappers keep legacy call sites working while routing every state
    # change through the transactional service layer.
    def verifikasi_pembayaran(self, is_approved: bool, actor=None, reason=''):
        from .services import verify_payment

        updated = verify_payment(self, approved=is_approved, actor=actor, reason=reason)
        if updated is not self:
            # The service works on a select_for_update() copy; mirror the
            # persisted state back onto this instance for legacy callers.
            for field in self._meta.concrete_fields:
                setattr(self, field.attname, getattr(updated, field.attname))
        return updated

    def mark_refund_pending(self, reason=''):
        self.status_pembayaran = self.REFUND_PENDING
        self.refund_requested_at = timezone.now()
        if reason:
            self.failure_reason = reason
        self.save(update_fields=[
            'status_pembayaran', 'refund_requested_at', 'failure_reason', 'updated_at',
        ])
        return self

    def mark_refunded(self, actor=None, reason=''):
        self.status_pembayaran = self.REFUNDED
        self.refunded_at = timezone.now()
        if actor is not None:
            self.verified_by = actor
        if reason:
            self.failure_reason = reason
        self.save(update_fields=[
            'status_pembayaran', 'refunded_at', 'verified_by',
            'failure_reason', 'updated_at',
        ])
        return self


class PaymentEvent(BaseTransaction):
    """Idempotency ledger for signed payment-gateway webhooks."""

    provider = models.CharField(max_length=30, default='generic')
    event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gateway_events',
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    class Meta:
        db_table = 'payment_events'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider}:{self.event_id}'


class Review(BaseTransaction):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    class Meta:
        db_table = 'reviews'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name='review_rating_1_to_5',
            ),
        ]

    def __str__(self):
        return f'Review {self.booking.booking_code} - {self.rating}/5'

    @property
    def display_name(self):
        """Full name when the guest shared one, username otherwise."""
        return self.guest.get_full_name().strip() or self.guest.username

    @property
    def initials(self):
        """Two-letter monogram used by the avatar in review cards."""
        parts = [part for part in self.display_name.replace('.', ' ').split() if part]
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.display_name[:2].upper()
