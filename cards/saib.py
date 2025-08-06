"""
This module provides the configuration for the SAIB Bank."""
from models import CashbackTier, CreditCard, TierCategory, categories


def get_saib_card() -> CreditCard:
    """Return SAIB Cashback credit card configuration with detailed tiers."""

    saib_tiers = [
        CashbackTier(
            name="Tier 1 (0K-3K)", min_spend=0, max_spend=2999, base_rate=0.0,
            categories={}
        ),
        CashbackTier(
            name="Tier 2 (3K-10K)", min_spend=3000, max_spend=9999, base_rate=0.005,
            categories={
                categories["grocery"]: TierCategory(rate=0.03, cap=100),
                categories["education"]: TierCategory(rate=0.03, cap=200),
                categories["dining"]: TierCategory(rate=0.03, cap=200),
                categories["gas_station"]: TierCategory(rate=0.03, cap=100),
            }
        ),
        CashbackTier(
            name="Tier 3 (10K-15K)", min_spend=10000, max_spend=14999, base_rate=0.005,
            categories={
                categories["grocery"]: TierCategory(rate=0.05, cap=100),
                categories["education"]: TierCategory(rate=0.05, cap=200),
                categories["dining"]: TierCategory(rate=0.05, cap=200),
                categories["gas_station"]: TierCategory(rate=0.05, cap=100),
            }
        ),
        CashbackTier(
            name="Tier 4 (15K+)", min_spend=15000, max_spend=float('inf'), base_rate=0.005,
            categories={
                categories["grocery"]: TierCategory(rate=0.1, cap=100),
                categories["education"]: TierCategory(rate=0.1, cap=200),
                categories["dining"]: TierCategory(rate=0.1, cap=200),
                categories["gas_station"]: TierCategory(rate=0.1, cap=100),
            }
        ),
    ]

    return CreditCard(
        name="SAIB Cashback",
        reference_link="https://www.saib.com.sa/ar/platinum-cashback-credit-card",
        annual_fee=399,
        tiers=saib_tiers,
    )