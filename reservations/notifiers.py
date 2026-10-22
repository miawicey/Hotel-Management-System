from abc import ABC, abstractmethod
from django.core.mail import send_mail


class Notifier(ABC):  
    @abstractmethod
    def send(self, user, message):
        ...


class EmailNotifier(Notifier):  
    def send(self, user, message):
        send_mail('Nocturn Haven - Booking', message, None, [user.email])


class ConsoleNotifier(Notifier):
    def send(self, user, message):
        print(f'[NOTIF] ke {user.username}: {message}')