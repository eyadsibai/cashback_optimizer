"""
This module provides the configuration for the Alrajhi Bank.
"""

from models import CardCategory, CreditCard, categories


def get_alrajhi_card() -> CreditCard:
    """Return Alrajhi Signature Cashback Plus credit card configuration."""
    return CreditCard(
        name="Alrajhi Signature Cashback Plus",
        reference_link=(
            "https://www.alrajhibank.com.sa/en/Personal/Cards/Cashback-Cards/"
            "Signature-Cashback-Plus"
        ),
        annual_fee=450,
        monthly_cap=500,
        grouped_monthly_caps=[
            (
                200,
                [
                    categories["international_spend_non_eur"],
                    categories["other_local_spend"],
                ],
            )
        ],
        categories={
            categories["dining"]: CardCategory(rate=0.10, cap=200),
            categories["grocery"]: CardCategory(rate=0.06, cap=200),
            categories["online_shopping_local"]: CardCategory(rate=0.02, cap=50),
            categories["international_spend_non_eur"]: CardCategory(rate=0.015),
        },
        base_rate=0.005,
        annual_cap=6000,
    )
