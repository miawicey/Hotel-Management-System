from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

<<<<<<< HEAD
=======
from core.models import TimeStampedModel

>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63

class RoomServiceMenuItem(models.Model):
    """A dish or drink that guests can order through the room-service portal.

    ``category`` is the guest-facing menu group.  ``subcategory`` adds the
    finer classification requested by the kitchen (Nasi Goreng, Sup, Mie,
    Makanan Utama, Refresher, Jus, Kopi, Teh) while ``is_recommended`` powers
    the chef's-recommendation rail without duplicating rows.
    """

    CATEGORY_HEAVY_MEAL = 'HEAVY_MEAL'
    CATEGORY_DRINK = 'DRINK'
    CATEGORY_DESSERT = 'DESSERT'

    CATEGORY_CHOICES = [
        (CATEGORY_HEAVY_MEAL, 'Makanan Berat'),
        (CATEGORY_DRINK, 'Minuman'),
        (CATEGORY_DESSERT, 'Hidangan Penutup'),
    ]

    SUB_NASI_GORENG = 'NASI_GORENG'
    SUB_SUP = 'SUP'
    SUB_MIE = 'MIE'
    SUB_MAIN_COURSE = 'MAIN_COURSE'
    SUB_REFRESHER = 'REFRESHER'
    SUB_JUICE = 'JUICE'
    SUB_COFFEE = 'COFFEE'
    SUB_TEA = 'TEA'
    SUB_DESSERT = 'DESSERT'

    SUBCATEGORY_CHOICES = [
        (SUB_NASI_GORENG, 'Nasi Goreng'),
        (SUB_SUP, 'Sup'),
        (SUB_MIE, 'Mie'),
        (SUB_MAIN_COURSE, 'Makanan Utama'),
        (SUB_REFRESHER, 'Refresher'),
        (SUB_JUICE, 'Jus'),
        (SUB_COFFEE, 'Kopi'),
        (SUB_TEA, 'Teh'),
        (SUB_DESSERT, 'Hidangan Penutup'),
    ]

    # Ordered structure consumed by the portal and the AI concierge context.
    MENU_STRUCTURE = [
        {
            'key': CATEGORY_HEAVY_MEAL,
            'label': 'Makanan Berat',
            'description': 'Hidangan hangat dari dapur utama, disiapkan saat dipesan.',
            'subcategories': [
                (SUB_NASI_GORENG, 'Nasi Goreng'),
                (SUB_SUP, 'Sup'),
                (SUB_MIE, 'Mie'),
                (SUB_MAIN_COURSE, 'Makanan Utama'),
            ],
        },
        {
            'key': CATEGORY_DRINK,
            'label': 'Minuman',
            'description': 'Dari mocktail segar hingga kopi dan teh pilihan.',
            'subcategories': [
                (SUB_REFRESHER, 'Refresher'),
                (SUB_JUICE, 'Jus'),
                (SUB_COFFEE, 'Kopi'),
                (SUB_TEA, 'Teh'),
            ],
        },
        {
            'key': CATEGORY_DESSERT,
            'label': 'Hidangan Penutup',
            'description': 'Penutup manis untuk menutup malam Anda.',
            'subcategories': [
                (SUB_DESSERT, 'Hidangan Penutup'),
            ],
        },
    ]

    SUBCATEGORIES_BY_CATEGORY = {
        group['key']: tuple(key for key, _label in group['subcategories'])
        for group in MENU_STRUCTURE
    }

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_HEAVY_MEAL,
    )
    subcategory = models.CharField(
        max_length=20, choices=SUBCATEGORY_CHOICES, default=SUB_MAIN_COURSE,
        db_index=True,
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    image_url = models.URLField(
        max_length=500, blank=True,
        help_text='URL foto stok berkualitas (Unsplash/Pexels) atau URL media hotel.',
    )
    is_recommended = models.BooleanField(
        default=False, db_index=True,
        help_text='Tampilkan di jalur Rekomendasi Chef.',
    )
    is_available = models.BooleanField(default=True, db_index=True)
    prep_minutes = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(5), MaxValueValidator(120)],
        help_text='Estimasi waktu penyiapan dalam menit.',
    )
    is_spicy = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'room_service_menu_items'
        ordering = ['category', 'subcategory', 'sort_order', 'name']
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['is_recommended', 'is_available']),
        ]

    def __str__(self):
        return f'{self.name} (Rp {self.price:,.0f})'.replace(',', '.')

    def clean(self):
        super().clean()
        allowed = self.SUBCATEGORIES_BY_CATEGORY.get(self.category, ())
        if self.subcategory not in allowed:
            raise ValidationError({
                'subcategory': 'Subkategori ini tidak sesuai dengan kategori menu.',
            })

    @property
    def category_label(self):
        return self.get_category_display()

    @property
    def subcategory_label(self):
        return self.get_subcategory_display()

    @property
    def section_label(self):
        return f'{self.get_category_display()} · {self.get_subcategory_display()}'


class ServiceOrder(models.Model):
<<<<<<< HEAD
    """A food & beverage order placed by a guest from an eligible stay."""
=======
    """A food & beverage order placed by a guest from an eligible stay.
    
    Demonstrates:
    - Encapsulation: status transitions controlled via transition_to() method
    - Polymorphism: behavior differs based on fulfillment (DELIVERY/PICKUP)
    """
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63

    FULFILLMENT_DELIVERY = 'DELIVERY'
    FULFILLMENT_PICKUP = 'PICKUP'

    FULFILLMENT_CHOICES = [
        (FULFILLMENT_DELIVERY, 'Antar ke Kamar'),
        (FULFILLMENT_PICKUP, 'Ambil / Makan di Restoran'),
    ]

    STATUS_INCOMING = 'INCOMING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_READY = 'READY'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_INCOMING, 'Pesanan Masuk'),
        (STATUS_PROCESSING, 'Sedang Diproses di Dapur'),
        (STATUS_DELIVERED, 'Makanan Diantar ke Kamar'),
        (STATUS_READY, 'Siap Disajikan di Restoran'),
        (STATUS_CANCELLED, 'Dibatalkan'),
    ]

    ACTIVE_STATUSES = (STATUS_INCOMING, STATUS_PROCESSING)
    COMPLETE_STATUSES = (STATUS_DELIVERED, STATUS_READY)
    FINAL_STATUSES = COMPLETE_STATUSES + (STATUS_CANCELLED,)

    STATUS_FLOW = {
        FULFILLMENT_DELIVERY: (
            STATUS_INCOMING, STATUS_PROCESSING, STATUS_DELIVERED,
        ),
        FULFILLMENT_PICKUP: (
            STATUS_INCOMING, STATUS_PROCESSING, STATUS_READY,
        ),
    }

    # Kitchen transitions.  Whether READY/DELIVERED is valid also depends on
    # the fulfillment method and is enforced by transition_to().
    ALLOWED_TRANSITIONS = {
        STATUS_INCOMING: (STATUS_PROCESSING, STATUS_CANCELLED),
        STATUS_PROCESSING: (STATUS_READY, STATUS_DELIVERED, STATUS_CANCELLED),
        STATUS_READY: (),
        STATUS_DELIVERED: (),
        STATUS_CANCELLED: (),
    }

    SERVICE_CHOICES = [
        ('FOOD', 'Makanan & Minuman'),
        ('AMENITIES', 'Request Amenities'),
        ('EXTRA_BED', 'Request Extra Bed'),
        ('LAUNDRY', 'Laundry'),
        ('RECEPTION', 'Chat dengan Resepsionis'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='service_orders',
    )
    booking = models.ForeignKey(
        'reservations.Booking', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='service_orders',
    )
    service_type = models.CharField(
        max_length=20, choices=SERVICE_CHOICES, default='FOOD',
    )
    fulfillment = models.CharField(
        max_length=20, choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_DELIVERY, db_index=True,
    )
    detail = models.TextField(blank=True, help_text='Ringkasan item pesanan.')
    special_instructions = models.TextField(
        blank=True,
        help_text='Permintaan khusus, misalnya tanpa pedas atau tanpa es.',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_INCOMING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'service_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return (
            f'{self.order_code} - {self.user} '
            f'({self.get_fulfillment_display()} / {self.get_status_display()})'
        )

    @property
    def order_code(self):
        return f'RS-{self.pk:04d}' if self.pk else 'RS-'

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0'))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def is_complete(self):
        return self.status in self.COMPLETE_STATUSES

    @property
    def is_pickup(self):
        return self.fulfillment == self.FULFILLMENT_PICKUP

    @property
    def status_flow(self):
        return self.STATUS_FLOW.get(self.fulfillment, self.STATUS_FLOW[self.FULFILLMENT_DELIVERY])

    @property
    def status_step_index(self):
        try:
            return self.status_flow.index(self.status)
        except ValueError:
            return -1

    @property
    def progress_percent(self):
        if self.status == self.STATUS_CANCELLED:
            return 0
        if self.status in self.COMPLETE_STATUSES:
            return 100
        return {self.STATUS_INCOMING: 18, self.STATUS_PROCESSING: 62}.get(self.status, 0)

    @property
    def status_tone(self):
        return {
            self.STATUS_INCOMING: 'incoming',
            self.STATUS_PROCESSING: 'processing',
            self.STATUS_READY: 'ready',
            self.STATUS_DELIVERED: 'delivered',
            self.STATUS_CANCELLED: 'cancelled',
        }.get(self.status, 'pending')

    @property
    def fulfillment_label(self):
        return self.get_fulfillment_display()

    @property
    def destination_label(self):
        if self.is_pickup:
            return 'The Grand Dining & Lounge'
        if self.booking_id and self.booking and self.booking.room_id:
            return f'Kamar {self.booking.room.number}'
        return 'Kamar Anda'

    @property
    def status_steps(self):
        """Three-step tracking model shared by the portal and detail page."""
        final_key = self.status_flow[-1]
        labels = {
            self.STATUS_INCOMING: 'Pesanan Masuk',
            self.STATUS_PROCESSING: 'Sedang Diproses di Dapur',
            self.STATUS_DELIVERED: 'Makanan Diantar ke Kamar',
            self.STATUS_READY: 'Siap Disajikan di Restoran',
        }
        descriptions = {
            self.STATUS_INCOMING: 'Pesanan diterima dan menunggu konfirmasi dapur.',
            self.STATUS_PROCESSING: 'Chef sedang menyiapkan pesanan Anda.',
            self.STATUS_DELIVERED: 'Pesanan dalam perjalanan menuju kamar Anda.',
            self.STATUS_READY: 'Silakan ambil atau nikmati di restoran hotel.',
        }
        current_index = self.status_step_index
        cancelled = self.status == self.STATUS_CANCELLED
        steps = []
        for index, key in enumerate(self.status_flow):
            if cancelled:
                state = 'done' if index == 0 else ''
            elif current_index >= 0 and index < current_index:
                state = 'done'
            elif current_index == index:
                state = 'current'
            else:
                state = ''
            steps.append({
                'key': key,
                'label': labels[key],
                'description': descriptions[key],
                'state': state,
                'is_last': key == final_key,
            })
        return steps

    @property
    def eta_minutes(self):
        """Kitchen estimate in minutes, including delivery or pickup handoff."""
        if not self.is_active:
            return 0
        prep = max(
            (item.menu_item.prep_minutes for item in self.items.all() if item.menu_item_id),
            default=20,
        )
        return min(prep + (8 if self.is_pickup else 12), 90)

<<<<<<< HEAD
    def transition_to(self, new_status, actor=None, note=''):
        """Move the order through the kitchen flow and write an audit log.

        Returns ``True`` when the transition is valid.  Invalid transitions are
        rejected instead of silently corrupting the guest's tracking view.
        """
        if new_status == self.status:
            return True
        if new_status not in self.ALLOWED_TRANSITIONS.get(self.status, ()):
=======
    def _can_transition(self, new_status):
        """Protected method: validasi kelayakan transisi status.
        Hanya bisa dipanggil dari dalam class ini.
        """
        if new_status == self.status:
            return True
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, ())
        if new_status not in allowed:
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
            return False
        if new_status == self.STATUS_READY and not self.is_pickup:
            return False
        if new_status == self.STATUS_DELIVERED and self.is_pickup:
            return False
<<<<<<< HEAD

=======
        return True

    def transition_to(self, new_status, actor=None, note=''):
        """Move the order through the kitchen flow and write an audit log.

        ENCAPSULATION: Satu-satunya cara resmi untuk mengubah status pesanan.
        Tidak boleh mengubah self.status secara langsung dari luar.
        
        POLYMORPHISM: Transisi bergantung pada fulfillment (DELIVERY/PICKUP).
        
        Returns ``True`` when the transition is valid.  Invalid transitions are
        rejected instead of silently corrupting the guest's tracking view.
        """
        if not self._can_transition(new_status):
            return False

        old_status = self.status
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        ServiceOrderStatusLog.objects.create(
            order=self, status=new_status, note=note or '', changed_by=actor,
        )
        return True

<<<<<<< HEAD
=======
    @property
    def is_editable_by_kitchen(self):
        """Protected logic exposed as property: apakah masih bisa diubah dapur."""
        return not self.is_final and self.status in self.ACTIVE_STATUSES

>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63

class ServiceOrderItem(models.Model):
    """A priced line item.  Chatbot-created orders may not have line items."""

    order = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name='items',
    )
    menu_item = models.ForeignKey(
        RoomServiceMenuItem, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='order_items',
    )
    name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)],
    )

    class Meta:
        db_table = 'room_service_order_items'
        ordering = ['pk']

    def __str__(self):
        return f'{self.name} x{self.quantity}'

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class ServiceOrderStatusLog(models.Model):
    """Audit trail for room-service order transitions."""

    order = models.ForeignKey(
        ServiceOrder, on_delete=models.CASCADE, related_name='status_logs',
    )
    status = models.CharField(max_length=20, choices=ServiceOrder.STATUS_CHOICES)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='service_order_status_changes',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'room_service_order_status_logs'
        ordering = ['created_at', 'pk']

    def __str__(self):
        return f'{self.order_id} -> {self.status}'
