import math
import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

pandas = pytest.importorskip("pandas")

from models import (
    CardCategory,
    CashbackTier,
    CreditCard,
    LifestyleCard,
    LifestylePlan,
    TierCategory,
    categories,
)
from optimizer import solve_optimization


def _monthly_spend(amounts):
    return {categories[key].key: value for key, value in amounts.items()}


def _extract_card_spend(result_df, card_name):
    if result_df.empty:
        return 0.0
    return result_df[result_df["Card"] == card_name]["Amount"].sum()


def test_dropping_fee_heavy_card_matches_removing_it():
    flat_card = CreditCard(
        name="FlatSaver",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.02,
    )
    fee_card = CreditCard(
        name="FeeTrap",
        reference_link="",
        annual_fee=500.0,
        base_rate=0.02,
    )
    monthly_spend = _monthly_spend({"other_local_spend": 2000.0})

    with_fee_result = solve_optimization([flat_card, fee_card], monthly_spend)
    without_fee_result = solve_optimization([flat_card], monthly_spend)

    assert with_fee_result is not None
    assert without_fee_result is not None

    assert math.isclose(
        with_fee_result.total_savings,
        without_fee_result.total_savings,
        rel_tol=1e-7,
        abs_tol=1e-6,
    )
    # Ensure the optimizer did not allocate spend to the fee-heavy card.
    assert _extract_card_spend(with_fee_result.results_df, "FeeTrap") == pytest.approx(0.0)


def test_tiered_card_cannot_earn_without_activation():
    baseline_card = CreditCard(
        name="Baseline",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.02,
    )
    tiered_card = CreditCard(
        name="TieredWindfall",
        reference_link="",
        annual_fee=500.0,
        base_rate=0.01,
        tiers=[
            CashbackTier(
                name="Bonus",
                min_spend=0.0,
                max_spend=float("inf"),
                categories={
                    categories["dining"]: TierCategory(rate=0.05),
                },
                base_rate=0.01,
            )
        ],
    )

    monthly_spend = _monthly_spend({"dining": 800.0})

    result = solve_optimization([baseline_card, tiered_card], monthly_spend)
    assert result is not None

    tiered_spend = _extract_card_spend(result.results_df, "TieredWindfall")
    baseline_spend = _extract_card_spend(result.results_df, "Baseline")

    assert tiered_spend == pytest.approx(0.0)
    assert baseline_spend == pytest.approx(800.0)

    baseline_only = solve_optimization([baseline_card], monthly_spend)
    assert baseline_only is not None
    assert result.total_savings == pytest.approx(baseline_only.total_savings)


def test_tiered_card_respects_minimum_spend_requirement():
    baseline_card = CreditCard(
        name="Baseline", reference_link="", annual_fee=0.0, base_rate=0.01
    )
    tiered_card = CreditCard(
        name="TieredThreshold",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.0,
        min_spend_for_cashback=500.0,
        tiers=[
            CashbackTier(
                name="FlatBonus",
                min_spend=0.0,
                max_spend=float("inf"),
                categories={
                    categories["dining"]: TierCategory(rate=0.05),
                },
                base_rate=0.0,
            )
        ],
    )

    low_spend = _monthly_spend({"dining": 300.0})
    low_result = solve_optimization([baseline_card, tiered_card], low_spend)

    assert low_result is not None
    assert _extract_card_spend(low_result.results_df, "TieredThreshold") == pytest.approx(0.0)
    assert _extract_card_spend(low_result.results_df, "Baseline") == pytest.approx(300.0)

    baseline_only_low = solve_optimization([baseline_card], low_spend)
    assert baseline_only_low is not None
    assert low_result.total_savings == pytest.approx(baseline_only_low.total_savings)

    qualifying_spend = _monthly_spend({"dining": 600.0})
    qualifying_result = solve_optimization(
        [baseline_card, tiered_card], qualifying_spend
    )

    assert qualifying_result is not None
    assert _extract_card_spend(
        qualifying_result.results_df, "TieredThreshold"
    ) == pytest.approx(600.0)
    assert _extract_card_spend(
        qualifying_result.results_df, "Baseline"
    ) == pytest.approx(0.0)

    expected_savings = 600.0 * 0.05 * 12
    assert qualifying_result.total_savings == pytest.approx(expected_savings)


def test_minimum_spend_card_gets_deactivated_when_requirement_unmet():
    baseline_card = CreditCard(
        name="Baseline",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.01,
    )
    bonus_card = CreditCard(
        name="BonusDining",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.0,
        min_spend_for_cashback=500.0,
        categories={
            categories["dining"]: CardCategory(rate=0.05),
        },
    )
    monthly_spend = _monthly_spend({"dining": 300.0})

    result = solve_optimization([baseline_card, bonus_card], monthly_spend)
    assert result is not None

    # All dining spend should fall back to the baseline card because the bonus card
    # cannot meet its minimum spend requirement.
    assert _extract_card_spend(result.results_df, "BonusDining") == pytest.approx(0.0)
    assert _extract_card_spend(result.results_df, "Baseline") == pytest.approx(300.0)

    # The bonus card should not improve the total savings compared to using only the baseline card.
    baseline_only = solve_optimization([baseline_card], monthly_spend)
    assert baseline_only is not None
    assert result.total_savings == pytest.approx(baseline_only.total_savings)


def test_tiered_cashback_activates_correct_tier():
    """Test that tiered cashback cards correctly activate the appropriate tier."""
    from models import CashbackTier, TierCategory

    tiered_card = CreditCard(
        name="TieredCard",
        reference_link="",
        annual_fee=0.0,
        tiers=[
            CashbackTier(
                name="Tier 1",
                min_spend=0,
                max_spend=1999,
                base_rate=0.01,
                categories={
                    categories["dining"]: TierCategory(rate=0.02, cap=50),
                },
            ),
            CashbackTier(
                name="Tier 2",
                min_spend=2000,
                max_spend=float("inf"),
                base_rate=0.01,
                categories={
                    categories["dining"]: TierCategory(rate=0.05, cap=100),
                },
            ),
        ],
    )
    
    # Test with spending in Tier 1 range
    monthly_spend_tier1 = _monthly_spend({"dining": 1500.0})
    result_tier1 = solve_optimization([tiered_card], monthly_spend_tier1)
    assert result_tier1 is not None
    # Expected cashback: 1500 * 0.02 = 30 (under the 50 cap)
    expected_tier1 = 30.0 * 12  # Annual savings
    assert result_tier1.total_savings == pytest.approx(expected_tier1, abs=1e-6)
    
    # Test with spending in Tier 2 range
    monthly_spend_tier2 = _monthly_spend({"dining": 2000.0})
    result_tier2 = solve_optimization([tiered_card], monthly_spend_tier2)
    assert result_tier2 is not None
    # Expected cashback: min(2000 * 0.05, 100) = 100
    expected_tier2 = 100.0 * 12  # Annual savings
    assert result_tier2.total_savings == pytest.approx(expected_tier2, abs=1e-6)


def test_tiered_cashback_respects_category_caps():
    """Test that tiered cashback cards respect individual category caps."""
    from models import CashbackTier, TierCategory

    # Create a baseline card with low rate but no caps
    baseline_card = CreditCard(
        name="BaselineCard",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.01,
    )
    
    # Create a tiered card with higher rate but strict caps
    tiered_card = CreditCard(
        name="TieredCapCard",
        reference_link="",
        annual_fee=0.0,
        tiers=[
            CashbackTier(
                name="Single Tier",
                min_spend=0,
                max_spend=float("inf"),
                base_rate=0.01,
                categories={
                    categories["dining"]: TierCategory(rate=0.10, cap=50),
                    categories["grocery"]: TierCategory(rate=0.10, cap=30),
                },
            ),
        ],
    )
    
    # User spends enough that the caps should be hit
    monthly_spend = _monthly_spend({"dining": 1000.0, "grocery": 500.0})
    result = solve_optimization([baseline_card, tiered_card], monthly_spend)
    assert result is not None
    
    # The optimizer should allocate spending optimally:
    # - For dining: 500 SAR to tiered card (minimum spend needed to reach 50 SAR cashback cap at 10% rate)
    #               500 SAR to baseline card (remaining spend, 5 SAR cashback at 1%)
    # - For grocery: 300 SAR to tiered card (minimum spend needed to reach 30 SAR cashback cap at 10% rate)
    #                200 SAR to baseline card (remaining spend, 2 SAR cashback at 1%)
    # Total cashback per month: 50 + 30 + 5 + 2 = 87 SAR
    # Annual savings: 87 * 12 = 1044 SAR
    expected_savings = (50 + 30 + 5 + 2) * 12
    assert result.total_savings == pytest.approx(expected_savings, abs=1e-6)
