from .base import BasePaymentProcessor


class ManualTransferProcessor(BasePaymentProcessor):
    """Concrete processor for manual bank transfer (current implementation)."""

    def charge(self, booking, amount):
        """For manual transfer, charge means waiting for proof upload."""
        return {
            "method": "MANUAL_TRANSFER",
            "status": "PENDING_VERIFICATION",
            "message": "Silakan upload bukti transfer untuk verifikasi."
        }

    def refund(self, payment, amount):
        """Route refund through the transactional service layer."""
        from ..services import request_refund
        request_refund(payment, reason="Refund via manual transfer")
        return {
            "method": "MANUAL_TRANSFER",
            "status": "REFUND_PENDING",
            "message": "Refund sedang diproses."
        }

    def get_method_name(self):
        return "Transfer Bank Manual"
