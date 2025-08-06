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
            categories={
                categories['dining']: CardCategory(rate=0.10),
                categories['travel_and_hotels']: CardCategory(rate=0.02),
                categories['grocery']: CardCategory(rate=0.05),
                categories['education']: CardCategory(rate=0.05),
                categories['medical_care']: CardCategory(rate=0.05),
            },
            base_rate=0.005,
        )