"""
This module provides the configuration for the NBD Bank.
"""""
from models import CardCategory, CreditCard, categories


def get_nbd_card() -> CreditCard:
    """Return NBD Cashback credit card configuration."""
    return CreditCard(
            name="Mazeed Platinum Cashback",
            reference_link="https://www.emiratesnbd.com.sa/en/cards/credit-cards/mazeed-platinum-credit-card",
            annual_fee=200,
            min_spend_for_cashback=1000, # Minimum spend to unlock cashback
            categories={
                categories['dining']: CardCategory(rate=0.10, cap=200),
                categories['travel_hotels']: CardCategory(rate=0.02, cap=200),
                categories['grocery']: CardCategory(rate=0.05, cap=200),
                categories['education']: CardCategory(rate=0.05, cap=200),
                categories['medical_care']: CardCategory(rate=0.05, cap=200),
            },
            base_rate=0.005,
        )