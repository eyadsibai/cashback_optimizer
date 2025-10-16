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


def test_tiered_card_selects_highest_available_tier():
    tier_card = CreditCard(
        name="TieredPro",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.01,
        tiers=[
            CashbackTier(
                name="Basic",
                min_spend=0.0,
                max_spend=499.99,
                categories={
                    categories["dining"]: TierCategory(rate=0.02),
                },
                base_rate=0.01,
            ),
            CashbackTier(
                name="Preferred",
                min_spend=500.0,
                max_spend=float("inf"),
                categories={
                    categories["dining"]: TierCategory(rate=0.05),
                },
                base_rate=0.01,
            ),
        ],
    )

    monthly_spend = _monthly_spend({"dining": 600.0})
    result = solve_optimization([tier_card], monthly_spend)

    assert result is not None
    assert _extract_card_spend(result.results_df, "TieredPro") == pytest.approx(600.0)
    assert result.total_savings == pytest.approx(600.0 * 0.05 * 12)


def test_lifestyle_plan_with_matching_bonus_is_selected():
    lifestyle_card = LifestyleCard(
        name="LifeMax",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.01,
        plans=[
            LifestylePlan(
                name="DiningPlan",
                categories_rate_cap=[
                    {categories["dining"]: CardCategory(rate=0.04)},
                ],
            ),
            LifestylePlan(
                name="GroceryPlan",
                categories_rate_cap=[
                    {categories["grocery"]: CardCategory(rate=0.07)},
                ],
            ),
        ],
    )

    monthly_spend = _monthly_spend({"grocery": 800.0})
    result = solve_optimization([lifestyle_card], monthly_spend)

    assert result is not None
    assert result.chosen_plan == "GroceryPlan"
    assert _extract_card_spend(result.results_df, "LifeMax") == pytest.approx(800.0)
    assert result.total_savings == pytest.approx(800.0 * 0.07 * 12)


def test_grouped_cap_limits_bonus_spend():
    combo_card = CreditCard(
        name="ComboRewards",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.01,
        categories={
            categories["dining"]: CardCategory(rate=0.05),
            categories["grocery"]: CardCategory(rate=0.05),
        },
        grouped_monthly_caps=[
            (30.0, [categories["dining"], categories["grocery"]]),
        ],
    )
    fallback_card = CreditCard(
        name="Fallback",
        reference_link="",
        annual_fee=0.0,
        base_rate=0.01,
    )

    monthly_spend = _monthly_spend({"dining": 400.0, "grocery": 400.0})
    result = solve_optimization([combo_card, fallback_card], monthly_spend)

    assert result is not None
    combo_spend = _extract_card_spend(result.results_df, "ComboRewards")
    fallback_spend = _extract_card_spend(result.results_df, "Fallback")

    assert combo_spend + fallback_spend == pytest.approx(800.0)
    assert combo_spend == pytest.approx(600.0, abs=1e-2)
    assert fallback_spend == pytest.approx(200.0, abs=1e-2)

    expected_monthly_cashback = (combo_spend * 0.05) + (fallback_spend * 0.01)
    assert result.total_savings == pytest.approx(expected_monthly_cashback * 12)
