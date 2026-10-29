"""Duck typing demonstration for polymorphism.

Any object that implements send(self, to, message) can be used
by notify_all() regardless of its class hierarchy.
"""


class NotificationChannel:
    """Base interface marker (duck typing style)."""

    def send(self, to, message):
        raise NotImplementedError


class EmailNotifier(NotificationChannel):
    def __init__(self, email_address=None):
        self.email_address = email_address

    def send(self, to, message):
        recipient = to or self.email_address or 'unknown'
        print(f"[EMAIL -> {recipient}] {message}")


class SMSNotifier(NotificationChannel):
    def __init__(self, phone_number=None):
        self.phone_number = phone_number

    def send(self, to, message):
        recipient = to or self.phone_number or 'unknown'
        print(f"[SMS -> {recipient}] {message}")


class InAppNotifier(NotificationChannel):
    def __init__(self, device_id=None):
        self.device_id = device_id

    def send(self, to, message):
        recipient = to or self.device_id or 'app'
        print(f"[IN-APP -> {recipient}] {message}")


def notify_all(channels, to, message):
    """Polymorphic function using duck typing."""
    for channel in channels:
        channel.send(to, message)
