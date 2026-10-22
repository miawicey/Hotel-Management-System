from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from reservations.models import Booking

from .menu import available_menu
from .models import (
    RoomServiceMenuItem,
    ServiceOrder,
    ServiceOrderItem,
    ServiceOrderStatusLog,
)

MAX_ORDER_LINES = 15
MAX_ORDER_TOTAL = Decimal('3000000')


class ServiceOrderForm(forms.Form):
    """Structured room-service order built from the live menu.

    Only stays that are active or upcoming for the logged-in guest are
    selectable.  Prices are copied server-side from the menu, never from POST
    data, so a guest cannot tamper with the invoice.
    """

    booking = forms.ModelChoiceField(
        queryset=Booking.objects.none(),
        label='Hubungkan ke reservasi',
        empty_label='— Pilih reservasi —',
        widget=forms.Select(attrs={'class': 'nh-input'}),
    )
    fulfillment = forms.ChoiceField(
        choices=ServiceOrder.FULFILLMENT_CHOICES,
        initial=ServiceOrder.FULFILLMENT_DELIVERY,
        label='Metode penyajian',
        widget=forms.RadioSelect(attrs={'class': 'nh-rs-fulfillment-input'}),
    )
    special_instructions = forms.CharField(
        label='Catatan untuk dapur',
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'nh-input nh-textarea',
            'rows': 3,
            'placeholder': 'Contoh: tanpa pedas, tanpa es, antar pukul 19:00',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        self.menu_items = available_menu()
        super().__init__(*args, **kwargs)

        today = timezone.localdate()
        self.eligible_bookings = (
            Booking.objects.filter(
                user=user,
                status_pesanan__in=Booking.SERVICE_ELIGIBLE_STATUSES,
                tanggal_check_out__gte=today,
            )
            .select_related('room', 'room__room_type')
            .order_by('tanggal_check_in')
        )
        self.fields['booking'].queryset = self.eligible_bookings

        bookings = list(self.eligible_bookings)
        primary = next(
            (booking for booking in bookings
             if booking.status_pesanan == 'CHECKED_IN'),
            bookings[0] if bookings else None,
        )
        if primary is not None:
            # Pre-select the active stay so a single eligible booking is
            # linked automatically; multi-stay guests can still change it.
            self.fields['booking'].initial = primary.pk

        for item in self.menu_items:
            self.fields[f'quantity_{item.pk}'] = forms.IntegerField(
                label=item.name,
                min_value=0,
                max_value=20,
                required=False,
                initial=0,
                widget=forms.NumberInput(attrs={
                    'class': 'qty-input',
                    'min': 0,
                    'max': 20,
                    'step': 1,
                    'inputmode': 'numeric',
                    'autocomplete': 'off',
                    'aria-label': f'Jumlah {item.name}',
                    'data-price': str(item.price),
                    'data-name': item.name,
                    'data-prep': item.prep_minutes,
                    'data-menu-id': item.pk,
                }),
            )
        self.estimated_total = Decimal('0')
        self.estimated_minutes = 0

    def clean(self):
        cleaned_data = super().clean()
        selected = []
        total = Decimal('0')
        prep = 0
        seen_ids = set()

        for item in self.menu_items:
            quantity = cleaned_data.get(f'quantity_{item.pk}') or 0
            if not quantity:
                continue
            if item.pk in seen_ids:
                raise ValidationError('Menu yang sama tidak boleh dipilih dua kali.')
            seen_ids.add(item.pk)
            selected.append((item, quantity))
            total += item.price * quantity
            prep = max(prep, item.prep_minutes)

        if not selected:
            raise ValidationError('Pilih minimal satu menu untuk dipesan.')
        if len(selected) > MAX_ORDER_LINES:
            raise ValidationError(
                f'Maksimal {MAX_ORDER_LINES} jenis menu dalam satu pesanan.'
            )
        if total > MAX_ORDER_TOTAL:
            raise ValidationError(
                'Total pesanan melebihi batas pemesanan otomatis. '
                'Silakan hubungi resepsionis untuk pesanan besar atau acara.'
            )

        self.cleaned_items = selected
        self.estimated_total = total
        fulfillment = cleaned_data.get('fulfillment')
        handoff = 8 if fulfillment == ServiceOrder.FULFILLMENT_PICKUP else 12
        self.estimated_minutes = min(prep + handoff, 90)
        return cleaned_data

    @transaction.atomic
    def save(self):
        booking = self.cleaned_data['booking']
        fulfillment = self.cleaned_data['fulfillment']

        # Re-read the menu inside the transaction: an item may have been
        # switched off while the guest was filling the form.
        fresh_rows = RoomServiceMenuItem.objects.select_for_update().filter(
            pk__in=[item.pk for item, _quantity in self.cleaned_items],
            is_available=True,
        )
        fresh_by_id = {item.pk: item for item in fresh_rows}
        unavailable = [
            item.name for item, _quantity in self.cleaned_items
            if item.pk not in fresh_by_id
        ]
        if unavailable:
            raise ValidationError(
                'Menu berikut baru saja tidak tersedia: '
                + ', '.join(unavailable)
                + '. Silakan perbarui pesanan Anda.'
            )

        priced_items = [
            (fresh_by_id[item.pk], quantity)
            for item, quantity in self.cleaned_items
        ]
        order = ServiceOrder.objects.create(
            user=self.user,
            booking=booking,
            service_type='FOOD',
            fulfillment=fulfillment,
            detail=', '.join(
                f'{item.name} x{quantity}' for item, quantity in priced_items
            ),
            special_instructions=self.cleaned_data.get(
                'special_instructions', ''
            ).strip(),
            status=ServiceOrder.STATUS_INCOMING,
        )
        for item, quantity in priced_items:
            ServiceOrderItem.objects.create(
                order=order,
                menu_item=item,
                name=item.name,
                unit_price=item.price,
                quantity=quantity,
            )
        ServiceOrderStatusLog.objects.create(
            order=order,
            status=ServiceOrder.STATUS_INCOMING,
            note=(
                'Pesanan dibuat dari portal room service '
                f'({order.get_fulfillment_display()}).'
            ),
            changed_by=self.user,
        )
        return order
