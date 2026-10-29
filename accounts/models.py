from django.contrib.auth.models import User
from django.db import models
<<<<<<< HEAD


class GuestProfile(models.Model):
    """Extended guest data that is not part of Django's User model."""
=======

from core.models import TimeStampedModel


class GuestProfile(models.Model):
    """Extended guest data that is not part of Django's User model.
    
    Demonstrates encapsulation via @property for computed values.
    """
>>>>>>> bec5b88e2e2dbe04431c4cb7c715a96b25f56c63

    ROLE_CHOICES = [
        ('GUEST', 'Guest'),
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
    ]
    STATUS_CHOICES = [('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')]
    LANGUAGE_CHOICES = [
        ('id', 'Bahasa Indonesia'),
        ('en', 'English'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='guest_profile',
    )
    phone_number = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    preferred_language = models.CharField(
        max_length=10, choices=LANGUAGE_CHOICES, default='id',
    )
    marketing_opt_in = models.BooleanField(
        default=False,
        help_text='Tamu bersedia menerima penawaran dan informasi dari Nocturn Haven.',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='GUEST')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name', 'user__email']

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.username

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.first_name or self.user.email

    @property
    def initials(self):
        name = self.user.get_full_name().strip()
        if not name:
            return (self.user.email or self.user.username or 'NH')[:2].upper()
        parts = [part for part in name.split() if part]
        return ''.join(part[0] for part in parts[:2]).upper()

    @property
    def completeness(self):
        """Percentage of the important profile fields that are filled in."""
        checks = [
            bool(self.user.first_name),
            bool(self.user.last_name),
            bool(self.user.email),
            bool(self.phone_number),
            bool(self.date_of_birth),
            bool(self.address),
        ]
        return round((sum(checks) / len(checks)) * 100)
