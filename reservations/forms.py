from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from rooms.models import Room

from .models import Booking, Payment, PromoVoucher, Review


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['room', 'tanggal_check_in', 'tanggal_check_out', 'jumlah_tamu', 'voucher']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'tanggal_check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tanggal_check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'jumlah_tamu': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'voucher': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.select_related('room_type').order_by('number')
        self.fields['room'].empty_label = '— Pilih kamar —'
        self.fields['voucher'].queryset = PromoVoucher.objects.order_by('kode_voucher')
        self.fields['voucher'].required = False
        self.fields['voucher'].empty_label = '— Tanpa voucher —'

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        check_in = cleaned_data.get('tanggal_check_in')
        check_out = cleaned_data.get('tanggal_check_out')
        guest_count = cleaned_data.get('jumlah_tamu')
        voucher = cleaned_data.get('voucher')

        if not room or not check_in or not check_out or not guest_count:
            return cleaned_data
        if check_out <= check_in:
            raise ValidationError('Tanggal check-out harus setelah check-in.')
        if guest_count > room.room_type.capacity:
            raise ValidationError(f'Kapasitas kamar maksimal {room.room_type.capacity} tamu.')
        if room.status != 'CLEAN' or not room.is_active:
            raise ValidationError('Kamar yang dipilih belum siap untuk dipesan.')
        if not Booking.available_rooms(check_in, check_out).filter(pk=room.pk).exists():
            raise ValidationError('Kamar tidak tersedia pada periode tersebut.')
        if voucher is not None:
            durasi = (check_out - check_in).days
            total_kamar = room.room_type.price_per_night * max(durasi, 1)
            if not voucher.is_valid(total_kamar):
                raise ValidationError(
                    'Voucher tidak berlaku (kedaluwarsa, kuota habis, atau minimum transaksi belum terpenuhi).'
                )
        return cleaned_data


class PaymentForm(forms.ModelForm):
    """Payment proof upload form.

    The amount is deliberately not editable here: the service layer always
    uses the booking total, so a tampered POST cannot change the invoice.
    """

    class Meta:
        model = Payment
        fields = ['metode_pembayaran', 'bukti_transfer_url']
        widgets = {
            'metode_pembayaran': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Transfer Bank BCA',
                'maxlength': 30,
            }),
            'bukti_transfer_url': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }
        help_texts = {
            'bukti_transfer_url': 'Format JPG, PNG, atau WEBP. Maksimal 5 MB.',
        }

    def clean_bukti_transfer_url(self):
        proof = self.cleaned_data.get('bukti_transfer_url')
        if not proof or not hasattr(proof, 'size'):
            return proof
        max_mb = getattr(settings, 'PAYMENT_PROOF_MAX_MB', 5)
        if proof.size > max_mb * 1024 * 1024:
            raise ValidationError(f'Ukuran bukti pembayaran maksimal {max_mb} MB.')
        content_type = getattr(proof, 'content_type', '')
        allowed = getattr(settings, 'PAYMENT_ALLOWED_PROOF_TYPES', (
            'image/jpeg', 'image/png', 'image/webp',
        ))
        if content_type and content_type not in allowed:
            raise ValidationError('Format bukti pembayaran harus JPG, PNG, atau WEBP.')
        return proof

    def clean_metode_pembayaran(self):
        value = self.cleaned_data['metode_pembayaran'].strip()
        if not value:
            raise ValidationError('Pilih metode pembayaran Anda.')
        return value


class ReviewForm(forms.ModelForm):
    """Rating is a five-star radio group instead of a bare number input."""

    RATING_CHOICES = [
        (5, '5 bintang'),
        (4, '4 bintang'),
        (3, '3 bintang'),
        (2, '2 bintang'),
        (1, '1 bintang'),
    ]

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        label='Rating',
        widget=forms.RadioSelect,
        error_messages={'required': 'Pilih rating bintang 1 sampai 5.'},
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Apa yang membuat menginap Anda berkesan?',
            }),
        }
