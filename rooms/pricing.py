from abc import ABC, abstractmethod
from decimal import Decimal


class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, base_price, nights): ...


class StandardPricing(PricingStrategy):                    
    def calculate(self, base_price, nights):
        return base_price * nights


class SuitePricing(PricingStrategy):
    def calculate(self, base_price, nights):
        total = base_price * nights
        return total * Decimal("0.9") if nights >= 7 else total  


_STRATEGIES = {
    "deluxe_king": StandardPricing(),
    "deluxe_twin": StandardPricing(),
    "executive_suite": SuitePricing(),
    "presidential_suite": SuitePricing(),
}


def get_pricing(room_type) -> PricingStrategy:
    return _STRATEGIES[room_type]