import math
import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

pandas = pytest.importorskip("pandas")

from models import CardCategory, CreditCard, categories
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
