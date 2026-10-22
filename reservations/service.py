from abc import ABC, abstractmethod
from .models import Reservation

class Notifier(ABC):
    @abstractmethod
    def send(self, to, message): ...


class EmailNotifier(Notifier):
    def send(self, to, message):
        print(f"Email ke {to}: {message}")


class WhatsAppNotifier(Notifier):
    def send(self, to, message):
        print(f"WA ke {to}: {message}")


#  kelas ini hanya mengurus logika booking
# bergantung pada abstraksi Notifier, bukan EmailNotifier langsung
class ReservationService:
    def __init__(self, notifier: Notifier):
        self.notifier = notifier

    def book(self, user, room, check_in, check_out):
        nights = (check_out - check_in).days
        room.reserve()
        reservation = Reservation.objects.create(
            user=user, room=room, check_in=check_in, check_out=check_out,
            total_price=room.total_price(nights),
        )
        self.notifier.send(user.email, f"Booking {room.name} berhasil!")
        return reservation