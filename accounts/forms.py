from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import GuestProfile


class AccountLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email', 'placeholder': 'contoh@email.com'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password', 'placeholder': 'Masukkan kata sandi'}))

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None
            self.user_cache = authenticate(self.request, username=user.username if user else email, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
            profile = getattr(self.user_cache, 'guest_profile', None)
            if profile and profile.status != GuestProfile.STATUS_CHOICES[0][0]:
                raise forms.ValidationError('Akun Anda sedang dinonaktifkan.', code='inactive')
        return self.cleaned_data


class AccountRegisterForm(UserCreationForm):
    full_name = forms.CharField(label='Nama lengkap', max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name', 'placeholder': 'Contoh: Alexander Wright'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email', 'placeholder': 'alexander.wright@luxurystay.com'}))
    phone_number = forms.CharField(label='Nomor telepon', max_length=30, widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel', 'placeholder': '+62 812-3456-7890'}))

    class Meta:
        model = User
        fields = ('full_name', 'email', 'phone_number', 'password1', 'password2')

    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password', 'placeholder': 'Min. 8 karakter'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password', 'placeholder': 'Ulangi kata sandi'}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email__iexact=email).exists() or GuestProfile.objects.filter(user__email__iexact=email).exists():
            raise forms.ValidationError('Email tersebut sudah terdaftar.')
        return email

    def save(self, commit=True):
        full_name = self.cleaned_data['full_name'].strip()
        first_name, _, last_name = full_name.partition(' ')
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = first_name
        user.last_name = last_name
        if commit:
            user.save()
            GuestProfile.objects.create(user=user, phone_number=self.cleaned_data['phone_number'])
        return user


class GuestProfileForm(forms.ModelForm):
    """Edit the User identity fields and the extended GuestProfile together."""

    full_name = forms.CharField(
        label='Nama lengkap',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'nh-input',
            'autocomplete': 'name',
            'placeholder': 'Nama sesuai KTP / paspor',
        }),
    )
    email = forms.EmailField(
        label='Alamat email',
        widget=forms.EmailInput(attrs={
            'class': 'nh-input',
            'autocomplete': 'email',
            'placeholder': 'nama@email.com',
        }),
    )

    class Meta:
        model = GuestProfile
        fields = [
            'phone_number', 'date_of_birth', 'address',
            'preferred_language', 'marketing_opt_in',
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'nh-input',
                'autocomplete': 'tel',
                'placeholder': '+62 812-3456-7890',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'nh-input',
                'type': 'date',
            }),
            'address': forms.Textarea(attrs={
                'class': 'nh-input nh-textarea',
                'rows': 3,
                'autocomplete': 'street-address',
                'placeholder': 'Alamat lengkap untuk keperluan registrasi tamu',
            }),
            'preferred_language': forms.Select(attrs={'class': 'nh-input'}),
            'marketing_opt_in': forms.CheckboxInput(attrs={'class': 'nh-checkbox'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None and not self.is_bound:
            self.fields['full_name'].initial = user.get_full_name()
            self.fields['email'].initial = user.email

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.user is not None:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('Email tersebut sudah digunakan akun lain.')
        return email

    def clean_date_of_birth(self):
        value = self.cleaned_data.get('date_of_birth')
        if value and value > timezone.localdate():
            raise forms.ValidationError('Tanggal lahir tidak boleh berada di masa depan.')
        return value

    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()
        if not value:
            raise forms.ValidationError('Nama lengkap wajib diisi.')
        return value

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = self.user or profile.user
        full_name = self.cleaned_data['full_name'].strip()
        user.first_name, _, user.last_name = full_name.partition(' ')
        user.email = self.cleaned_data['email']
        if commit:
            with transaction.atomic():
                user.save(update_fields=['first_name', 'last_name', 'email'])
                profile.save()
        return profile


class NocturnPasswordChangeForm(PasswordChangeForm):
    """Password change form with the guest portal input styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'nh-input', 'autocomplete': 'new-password'})
        self.fields['old_password'].widget.attrs['autocomplete'] = 'current-password'
