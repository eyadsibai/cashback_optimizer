"""
This module provides the configuration for the SNB Bank.
"""
# pylint: disable=duplicate-code

from models import CardCategory, CreditCard, categories


def get_nayfat_card() -> CreditCard:
    """Return Nayfat Platinum Cashback credit card configuration.

    Returns:
        CreditCard: Configured Nayfat Platinum Cashback card with categories,
                   rates, caps, and annual fee information.
    """
    return CreditCard(
        name="Nayfat Platinum Cashback",
        reference_link=(
            "https://www.alahli.com/en/pages/personal-banking/credit-cards/"
            "alahli-cashback-premium-credit-card"
        ),
        annual_fee=0,
        categories={
            categories["dining"]: CardCategory(rate=0.10),
            categories["medical_care"]: CardCategory(rate=0.05),
            categories["grocery"]: CardCategory(rate=0.03),
            categories["online_shopping_local"]: CardCategory(rate=0.02),
            categories["travel_hotels"]: CardCategory(rate=0.015),
        },
        base_rate=0.007,
        annual_cap=500
    )
