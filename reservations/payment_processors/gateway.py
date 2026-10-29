from .base import BasePaymentProcessor


class GatewayPaymentProcessor(BasePaymentProcessor):
    """Concrete processor for payment gateway (webhook-based)."""

    def charge(self, booking, amount):
        """Gateway payment flow - awaiting gateway confirmation."""
        return {
            "method": "GATEWAY",
            "status": "AWAITING_PAYMENT",
            "message": "Menunggu konfirmasi dari payment gateway."
        }

    def refund(self, payment, amount):
        """Gateway-initiated refund flow."""
        return {
            "method": "GATEWAY",
            "status": "REFUND_INITIATED",
            "message": "Permintaan refund ke payment gateway telah diajukan."
        }

    def get_method_name(self):
        return "Payment Gateway"
