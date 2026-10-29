from django.core.validators import MinValueValidator
from django.db import models
from .pricing import get_pricing



from core.models import TimeStampedModel

class RoomType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    capacity = models.PositiveIntegerField(default=2, validators=[MinValueValidator(1)])
 
    class Meta:
        db_table = 'room_types'
        ordering = ['name']
 
    def __str__(self):
        return self.name
 
 
class Room(models.Model):
    STATUS_CHOICES = [
        ('CLEAN', 'Clean'),
        ('DIRTY', 'Dirty'),
        ('MAINTENANCE', 'Maintenance'),
    ]
 
    number = models.CharField(max_length=10, unique=True)
    room_type = models.ForeignKey(
        RoomType, on_delete=models.PROTECT, related_name='rooms'
    )
    floor = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='CLEAN'
    )
    is_active = models.BooleanField(default=True)
 
    class Meta:
        db_table = 'rooms'
        ordering = ['number']
 
    def __str__(self):
        return f'Room {self.number} ({self.room_type})'


class RoomAvailability(models.Model): #ini buat ketersediaan room (?)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='availabilities'
    )
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
 
    class Meta:
        ordering = ['date']
        unique_together = ('room', 'date')
        verbose_name_plural = 'Room availabilities'
 
    def __str__(self):
        state = 'Available' if self.is_available else 'Blocked'
        return f'{self.room.number} - {self.date} - {state}'



class TimeStampedModel(models.Model):                      
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Room(TimeStampedModel):                              
    class RoomType(models.TextChoices):
        DELUXE_KING = "deluxe_king", "Kamar Deluxe King"
        DELUXE_TWIN = "deluxe_twin", "Kamar Deluxe Twin"
        EXECUTIVE_SUITE = "executive_suite", "Suite Eksekutif Horizon"
        PRESIDENTIAL_SUITE = "presidential_suite", "Grand Suite Presidensial"

    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=30, choices=RoomType.choices)
    capacity = models.PositiveSmallIntegerField(default=2)       # "2 tamu", "4 tamu"
    size_m2 = models.PositiveIntegerField()                      # 38, 65, 110
    view = models.CharField(max_length=100, blank=True)          # "Pemandangan kota"
    base_price = models.DecimalField(max_digits=12, decimal_places=0)  # Rp / malam

    # ENCAPSULATION: aturan ketersediaan ada di dalam Room, view tidak perlu tahu detailnya
    def is_available_for(self, check_in, check_out):
        return not self.reservations.filter(
            status__in=["pending", "confirmed"],
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exists()

    def total_price(self, nights):
        return get_pricing(self.room_type).calculate(self.base_price, nights)

    def __str__(self):
        return self.name
# Create your models here.
