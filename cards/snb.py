"""
This module provides the configuration for the SNB Bank.
"""
# pylint: disable=duplicate-code

from models import CardCategory, CreditCard, categories


def get_snb_card() -> CreditCard:
    """Return SNB Premium Cashback credit card configuration.

    Returns:
        CreditCard: Configured SNB Premium Cashback card with categories,
                   rates, caps, and annual fee information.
    """
    return CreditCard(
        name="SNB Premium Cashback",
        reference_link=(
            "https://www.alahli.com/en/pages/personal-banking/credit-cards/"
            "alahli-cashback-premium-credit-card"
        ),
        annual_fee=230,
        categories={
            categories["gas_station"]: CardCategory(rate=0.11, cap=100),
            categories["dining"]: CardCategory(rate=0.05, cap=200),
            categories["grocery"]: CardCategory(rate=0.05, cap=200),
            categories["pharmacy"]: CardCategory(rate=0.05, cap=200),
            categories["international_spend"]: CardCategory(rate=0.02),
        },
        base_rate=0.007,
        monthly_cap=700
    )
