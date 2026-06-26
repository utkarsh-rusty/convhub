from decimal import Decimal


class InsufficientCreditsError(Exception):
    def __init__(self, required: Decimal, available: Decimal) -> None:
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient credits: required {required}, available {available}",
        )
