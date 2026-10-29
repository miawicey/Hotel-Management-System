from abc import ABC, abstractmethod


class BasePaymentProcessor(ABC):
    """Abstract base class defining the payment processor contract.
    
    Demonstrates inheritance + abstraction + polymorphism:
    - All processors inherit from BasePaymentProcessor
    - Subclasses MUST implement charge() and refund()
    - Same interface used polymorphically regardless of concrete type
    """

    @abstractmethod
    def charge(self, booking, amount):
        """Process payment for a booking. Must be implemented by subclass."""
        pass

    @abstractmethod
    def refund(self, payment, amount):
        """Process refund for a payment. Must be implemented by subclass."""
        pass

    @abstractmethod
    def get_method_name(self):
        """Return the payment method name."""
        pass
