"""
This module provides the configuration for the SAIB Bank."""

from models import CashbackTier, CreditCard, TierCategory, categories


def get_sabb_card() -> CreditCard:
    """Return SABB Cashback credit card configuration with detailed tiers."""

    sabb_tiers = [
        CashbackTier(
            name="Tier 1 (0K-2K)",
            min_spend=0,
            max_spend=1999,
            base_rate=0.001,
            categories={
                categories["grocery"]: TierCategory(rate=0.0, cap=100),
                categories["dining"]: TierCategory(rate=0.0, cap=200),
                categories["gas_station"]: TierCategory(rate=0.0, cap=100),
            },
        ),
        CashbackTier(
            name="Tier 2 (2K-10K)",
            min_spend=2000,
            max_spend=9999,
            base_rate=0.001,
            categories={
                categories["grocery"]: TierCategory(rate=0.03, cap=100),
                categories["dining"]: TierCategory(rate=0.03, cap=200),
                categories["gas_station"]: TierCategory(rate=0.03, cap=100),
            },
        ),
        CashbackTier(
            name="Tier 3 (10K-15K)",
            min_spend=10000,
            max_spend=14999,
            base_rate=0.001,
            categories={
                 categories["grocery"]: TierCategory(rate=0.05, cap=100),
                categories["dining"]: TierCategory(rate=0.05, cap=200),
                categories["gas_station"]: TierCategory(rate=0.05, cap=100), },
        ),
        CashbackTier(
            name="Tier 4 (15K+)",
            min_spend=15000,
            max_spend=float("inf"),
            base_rate=0.001,
            categories={
              categories["grocery"]: TierCategory(rate=0.1, cap=100),
                categories["dining"]: TierCategory(rate=0.1, cap=200),
                categories["gas_station"]: TierCategory(rate=0.1, cap=100),
            },
        ),
    ]

    return CreditCard(
        name="SABB Cashback",
        reference_link="https://www.sab.com/en/personal/compare-credit-cards/cashback-visa-credit-card/",
        annual_fee=0,
        tiers=sabb_tiers,
        min_spend_for_cashback=1999
    )
