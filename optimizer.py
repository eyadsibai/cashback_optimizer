from typing import Dict, List, Tuple

import pandas as pd
from pulp import LpBinary, LpMaximize, LpProblem, LpVariable, lpSum  # type: ignore

from models import (
    CardCategory,
    CreditCard,
    LifestyleCard,
    OptimizationResult,
    TierCategory,
    categories,
)

LARGE_NUMBER = 1_000_000  # A large number for big-M method in LP


def _create_variables(
    cards: List[CreditCard],
) -> Tuple[Dict, Dict, Dict]:
    """Creates the decision variables for the optimization problem."""
    spend_vars = LpVariable.dicts(
        "Spend",
        ((c.name, cat.key) for c in cards for cat in categories.values()),
        lowBound=0,
    )

    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    plan_vars = {}
    activated_bonus_vars = {}
    if lifestyle_card:
        plan_vars = LpVariable.dicts(
            "PlanChoice", (p.name for p in lifestyle_card.plans), cat=LpBinary
        )
        activated_bonus_vars = LpVariable.dicts(
            "ActivatedBonus", (p.name for p in lifestyle_card.plans), lowBound=0
        )

    return spend_vars, plan_vars, activated_bonus_vars


def _add_tiered_cashback_logic(prob, card, total_spend_on_card, spend_vars):
    """Adds the logic for tiered cashback cards to the problem."""
    components = []
    tier_vars = LpVariable.dicts(
        f"TierChoice_{card.name}", (t.name for t in card.tiers), cat=LpBinary
    )
    prob += lpSum(tier_vars.values()) == 1, f"ChooseOneTier_{card.name}"

    for tier in card.tiers:
        y = tier_vars[tier.name]
        prob += total_spend_on_card >= tier.min_spend - LARGE_NUMBER * (1 - y)
        if tier.max_spend != float("inf"):
            prob += total_spend_on_card <= tier.max_spend + LARGE_NUMBER * (1 - y)

        for cat in categories.values():
            tier_cat = tier.categories.get(
                cat, TierCategory(rate=tier.base_rate, cap=float("inf"))
            )
            cashback = spend_vars[card.name, cat.key] * tier_cat.rate
            activated_cashback = LpVariable(
                f"Cashback_{card.name}_{tier.name}_{cat.key}", lowBound=0
            )
            prob += activated_cashback <= LARGE_NUMBER * y
            prob += activated_cashback <= cashback
            if tier_cat.cap != float("inf"):
                prob += cashback <= tier_cat.cap + LARGE_NUMBER * (1 - y)
            components.append(activated_cashback)
    return components


def _add_min_spend_cashback_logic(prob, card, total_spend_on_card, spend_vars):
    """Adds the logic for cards with a minimum spend requirement."""
    cashback_active = LpVariable(f"CashbackActive_{card.name}", cat=LpBinary)
    prob += total_spend_on_card >= card.min_spend_for_cashback - LARGE_NUMBER * (
        1 - cashback_active
    )
    prob += (
        total_spend_on_card
        <= (card.min_spend_for_cashback - 0.01) + LARGE_NUMBER * cashback_active
    )

    card_cashback = lpSum(
        spend_vars[card.name, cat.key]
        * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
        for cat in categories.values()
    )
    activated_cashback = LpVariable(f"ActivatedCashback_{card.name}", lowBound=0)
    prob += activated_cashback <= LARGE_NUMBER * cashback_active
    prob += activated_cashback <= card_cashback
    return [activated_cashback]


def _add_regular_cashback_logic(card, spend_vars):
    """Adds the logic for regular (non-tiered, non-min-spend) cards."""
    components = [
        lpSum(
            spend_vars[card.name, cat.key] * card.base_rate
            for cat in categories.values()
        )
    ]
    if not isinstance(card, LifestyleCard):
        for cat, card_cat in card.categories.items():
            bonus = spend_vars[card.name, cat.key] * (card_cat.rate - card.base_rate)
            components.append(bonus)
    return components


def _add_constraints(prob, cards, monthly_spending, spend_vars, plan_vars):
    """Adds all constraints to the optimization problem."""
    # Spending must match user's input
    for cat in categories.values():
        prob += (
            lpSum(spend_vars[c.name, cat.key] for c in cards)
            == monthly_spending.get(cat.key, 0),
            f"Spend_Total_{cat.key}",
        )

    # Card-specific constraints (caps, etc.)
    for card in cards:
        if card.tiers:
            continue  # Tier caps are handled in the tiered logic

        # Monthly cap for non-lifestyle, non-tiered cards
        if not isinstance(card, LifestyleCard) and card.monthly_cap != float("inf"):
            cashback = lpSum(
                spend_vars[card.name, cat.key]
                * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
                for cat in categories.values()
            )
            prob += cashback <= card.monthly_cap, f"MonthlyCap_{card.name}"

        # Individual category caps
        for cat, card_cat in card.categories.items():
            if card_cat.cap != float("inf"):
                prob += (
                    spend_vars[card.name, cat.key] * card_cat.rate <= card_cat.cap,
                    f"CatCap_{card.name}_{cat.key}",
                )

        # Grouped category caps
        if card.grouped_monthly_caps:
            for i, (cap, cat_list) in enumerate(card.grouped_monthly_caps):
                prob += (
                    lpSum(
                        spend_vars[card.name, c.key]
                        * card.categories.get(c, CardCategory(rate=card.base_rate)).rate
                        for c in cat_list
                    )
                    <= cap,
                    f"GroupCap_{card.name}_{i}",
                )

    # Lifestyle card plan constraints
    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    if lifestyle_card:
        prob += lpSum(plan_vars.values()) == 1, "Select_One_Lifestyle_Plan"
        for plan in lifestyle_card.plans:
            for i, group in enumerate(plan.categories_rate_cap):
                cap = list(group.values())[0].cap
                if cap != float("inf"):
                    cashback = lpSum(
                        spend_vars[lifestyle_card.name, cat.key] * cat_rate.rate
                        for cat, cat_rate in group.items()
                    )
                    prob += (
                        cashback <= cap + LARGE_NUMBER * (1 - plan_vars[plan.name]),
                        f"PlanCap_{plan.name}_{i}",
                    )


def _build_optimization_problem(
    cards: List[CreditCard], monthly_spending: Dict[str, float]
) -> Tuple[LpProblem, Dict, Dict]:
    """Builds and returns the PuLP optimization problem."""
    prob = LpProblem("Unified_Card_Optimizer", LpMaximize)
    spend_vars, plan_vars, activated_bonus_vars = _create_variables(cards)

    # --- Objective Function ---
    all_cashback = []
    for card in cards:
        total_spend = lpSum(
            spend_vars[card.name, cat.key] for cat in categories.values()
        )
        if card.tiers:
            all_cashback.extend(
                _add_tiered_cashback_logic(prob, card, total_spend, spend_vars)
            )
        elif card.min_spend_for_cashback > 0:
            all_cashback.extend(
                _add_min_spend_cashback_logic(prob, card, total_spend, spend_vars)
            )
        else:
            all_cashback.extend(_add_regular_cashback_logic(card, spend_vars))

    # Add lifestyle bonus to objective
    all_cashback.append(lpSum(activated_bonus_vars.values()))

    # Calculate total annual fees with new conditional logic
    total_annual_fees = []
    for card in cards:
        if card.minimum_annual_spend_for_fee_waiver is not None and card.minimum_annual_spend_for_fee_waiver > 0:
            fee_is_waived = LpVariable(f"FeeWaived_{card.name}", cat=LpBinary)
            annual_spend_on_card = lpSum(
                spend_vars[card.name, cat.key] for cat in categories.values()
            ) * 12
            prob += annual_spend_on_card >= card.minimum_annual_spend_for_fee_waiver - LARGE_NUMBER * (1 - fee_is_waived), f"Waived_Spend_Constraint_1_{card.name}"
            prob += annual_spend_on_card <= card.minimum_annual_spend_for_fee_waiver - 0.01 + LARGE_NUMBER * fee_is_waived, f"Waived_Spend_Constraint_2_{card.name}"
            annual_fee_to_pay = (fee_is_waived * card.annual_fee) + ((1 - fee_is_waived) * card.annual_fee_if_condition_not_met)
            total_annual_fees.append(annual_fee_to_pay)
        else:
            total_annual_fees.append(card.annual_fee)

    # Final objective function: Net Annual Savings
    total_monthly_cashback = lpSum(all_cashback)
    prob += (
        (total_monthly_cashback * 12) - lpSum(total_annual_fees),
        "Total_Net_Annual_Savings",
    )

    # --- Constraints ---
    _add_constraints(prob, cards, monthly_spending, spend_vars, plan_vars)

    # Link lifestyle bonus to objective
    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    if lifestyle_card:
        for plan in lifestyle_card.plans:
            potential_bonus = lpSum(
                spend_vars[lifestyle_card.name, cat.key]
                * (card_cat.rate - lifestyle_card.base_rate)
                for group in plan.categories_rate_cap
                for cat, card_cat in group.items()
            )
            prob += (
                activated_bonus_vars[plan.name] <= LARGE_NUMBER * plan_vars[plan.name]
            )
            prob += activated_bonus_vars[plan.name] <= potential_bonus
            prob += activated_bonus_vars[
                plan.name
            ] >= potential_bonus - LARGE_NUMBER * (1 - plan_vars[plan.name])

    return prob, spend_vars, plan_vars


def _process_optimization_results(
    prob: LpProblem,
    cards: List[CreditCard],
    spend_vars: Dict,
    plan_vars: Dict,
) -> OptimizationResult | None:
    """Processes the solved PuLP problem and returns the results."""
    results = [
        {
            "Card": c.name,
            "Category": cat.key,
            "Amount": spend_vars[c.name, cat.key].varValue,
        }
        for c in cards
        for cat in categories.values()
        if spend_vars[c.name, cat.key].varValue is not None
        and spend_vars[c.name, cat.key].varValue > 0.01
    ]

    chosen_plan_name = ""
    if plan_vars:
        chosen_plan_name = next(
            (p_name for p_name, var in plan_vars.items() if var.varValue > 0.9), ""
        )
    if prob.objective is None:
        return None
    objective_value = prob.objective.value()
    if objective_value is None:
        return None
    return OptimizationResult(
        results_df=pd.DataFrame(results),
        total_savings=float(objective_value),
        chosen_plan=chosen_plan_name,
    )


def solve_optimization(
    cards: List[CreditCard], monthly_spending: Dict[str, float]
) -> OptimizationResult | None:
    """Top-level function to solve the credit card optimization problem."""
    prob, spend_vars, plan_vars = _build_optimization_problem(cards, monthly_spending)
    prob.solve()

    if prob.status != 1:  # 1 means "Optimal"
        return None

    return _process_optimization_results(prob, cards, spend_vars, plan_vars)
