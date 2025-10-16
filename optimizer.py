from typing import Dict, List, Tuple

import pandas as pd
from pulp import (
    LpAffineExpression,
    LpBinary,
    LpMaximize,
    LpProblem,
    LpVariable,
    lpSum,
)  # type: ignore

from models import (
    Category,
    CreditCard,
    LifestyleCard,
    OptimizationResult,
    categories,
)

LARGE_NUMBER = 1_000_000  # A large number for big-M method in LP
ALL_CATEGORIES = tuple(categories.values())


def _rate_for_category(card: CreditCard, category: Category) -> float:
    """Return the cashback rate for a card/category combination."""

    card_category = card.categories.get(category)
    return card_category.rate if card_category else card.base_rate


def _card_cashback_value(card: CreditCard, spend_vars: Dict) -> LpAffineExpression:
    """Return the expression for total cashback at the category-specific rates."""

    return lpSum(
        spend_vars[card.name, cat.key] * _rate_for_category(card, cat)
        for cat in ALL_CATEGORIES
    )


def _create_variables(
    cards: List[CreditCard],
) -> Tuple[Dict, Dict, Dict, Dict]:
    """Creates the decision variables for the optimization problem."""
    spend_vars = LpVariable.dicts(
        "Spend",
        ((c.name, cat.key) for c in cards for cat in ALL_CATEGORIES),
        lowBound=0,
    )

    card_active_vars = LpVariable.dicts(
        "CardActive", (c.name for c in cards), cat=LpBinary
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

    return spend_vars, plan_vars, activated_bonus_vars, card_active_vars


def _add_tiered_cashback_logic(
    prob, card, total_spend_on_card, spend_vars, card_active_var
):
    """Adds the logic for tiered cashback cards to the problem."""
    components = []
    tier_vars = LpVariable.dicts(
        f"TierChoice_{card.name}", (t.name for t in card.tiers), cat=LpBinary
    )
    prob += (
        lpSum(tier_vars.values()) == card_active_var,
        f"ChooseTierIfActive_{card.name}",
    )

    for tier in card.tiers:
        y = tier_vars[tier.name]
        prob += total_spend_on_card >= tier.min_spend - LARGE_NUMBER * (1 - y)
        if tier.max_spend != float("inf"):
            prob += total_spend_on_card <= tier.max_spend + LARGE_NUMBER * (1 - y)

        for cat in ALL_CATEGORIES:
            tier_cat = tier.categories.get(cat)
            rate = tier_cat.rate if tier_cat else tier.base_rate
            cap = tier_cat.cap if tier_cat else float("inf")
            cashback = spend_vars[card.name, cat.key] * rate
            activated_cashback = LpVariable(
                f"Cashback_{card.name}_{tier.name}_{cat.key}", lowBound=0
            )
            prob += activated_cashback <= LARGE_NUMBER * y
            prob += activated_cashback <= cashback
            if cap != float("inf"):
                prob += cashback <= cap + LARGE_NUMBER * (1 - y)
            components.append(activated_cashback)
    return components


def _gate_cashback_by_min_spend(
    prob,
    card,
    total_spend_on_card,
    card_active_var,
    cashback_components,
):
    """Wrap cashback components so they only pay out when the spend minimum is met."""

    cashback_active = LpVariable(f"CashbackActive_{card.name}", cat=LpBinary)
    prob += cashback_active <= card_active_var

    min_spend = card.min_spend_for_cashback
    prob += total_spend_on_card >= min_spend - LARGE_NUMBER * (1 - cashback_active)
    prob += (
        total_spend_on_card
        <= (min_spend - 0.01)
        + LARGE_NUMBER * (cashback_active + (1 - card_active_var))
    )

    gated_components = []
    for index, component in enumerate(cashback_components):
        activated_cashback = LpVariable(
            f"ActivatedCashback_{card.name}_{index}", lowBound=0
        )
        prob += activated_cashback <= LARGE_NUMBER * cashback_active
        prob += activated_cashback <= component
        prob += activated_cashback >= component - LARGE_NUMBER * (1 - cashback_active)
        gated_components.append(activated_cashback)

    return gated_components


def _add_regular_cashback_logic(card, spend_vars):
    """Adds the logic for regular (non-tiered, non-min-spend) cards."""
    components = [
        lpSum(
            spend_vars[card.name, cat.key] * card.base_rate for cat in ALL_CATEGORIES
        )
    ]
    if not isinstance(card, LifestyleCard):
        for cat, card_cat in card.categories.items():
            bonus = spend_vars[card.name, cat.key] * (card_cat.rate - card.base_rate)
            components.append(bonus)
    return components


def _add_total_spend_constraints(prob, cards, monthly_spending, spend_vars):
    for cat in ALL_CATEGORIES:
        prob += (
            lpSum(spend_vars[c.name, cat.key] for c in cards)
            == monthly_spending.get(cat.key, 0),
            f"Spend_Total_{cat.key}",
        )


def _add_card_constraints(
    prob, card, total_monthly_spend, spend_vars, card_active_var
):
    total_spend_on_card = lpSum(
        spend_vars[card.name, cat.key] for cat in ALL_CATEGORIES
    )
    prob += (
        total_spend_on_card <= total_monthly_spend * card_active_var,
        f"TotalSpendLimit_{card.name}",
    )

    if not card.tiers:
        if (
            not isinstance(card, LifestyleCard)
            and card.monthly_cap != float("inf")
        ):
            cashback = _card_cashback_value(card, spend_vars)
            prob += (
                cashback <= card.monthly_cap * card_active_var,
                f"MonthlyCap_{card.name}",
            )

        for cat, card_cat in card.categories.items():
            if card_cat.cap != float("inf"):
                prob += (
                    spend_vars[card.name, cat.key] * card_cat.rate
                    <= card_cat.cap * card_active_var,
                    f"CatCap_{card.name}_{cat.key}",
                )

        for i, (cap, cat_list) in enumerate(card.grouped_monthly_caps):
            prob += (
                lpSum(
                    spend_vars[card.name, c.key] * _rate_for_category(card, c)
                    for c in cat_list
                )
                <= cap * card_active_var,
                f"GroupCap_{card.name}_{i}",
            )


def _add_lifestyle_plan_constraints(
    prob, lifestyle_card, plan_vars, spend_vars, card_active_var
):
    prob += (
        lpSum(plan_vars.values()) == card_active_var,
        "Select_One_Lifestyle_Plan",
    )
    for plan in lifestyle_card.plans:
        plan_var = plan_vars[plan.name]
        prob += plan_var <= card_active_var
        for i, group in enumerate(plan.categories_rate_cap):
            cap = next(iter(group.values())).cap
            if cap != float("inf"):
                cashback = lpSum(
                    spend_vars[lifestyle_card.name, cat.key] * cat_rate.rate
                    for cat, cat_rate in group.items()
                )
                prob += (
                    cashback <= cap + LARGE_NUMBER * (1 - plan_var),
                    f"PlanCap_{plan.name}_{i}",
                )


def _add_constraints(
    prob, cards, monthly_spending, spend_vars, plan_vars, card_active_vars
):
    """Adds all constraints to the optimization problem."""

    _add_total_spend_constraints(prob, cards, monthly_spending, spend_vars)

    total_monthly_spend = sum(monthly_spending.values())
    for card in cards:
        _add_card_constraints(
            prob,
            card,
            total_monthly_spend,
            spend_vars,
            card_active_vars[card.name],
        )

    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    if lifestyle_card:
        _add_lifestyle_plan_constraints(
            prob,
            lifestyle_card,
            plan_vars,
            spend_vars,
            card_active_vars[lifestyle_card.name],
        )


def _build_optimization_problem(
    cards: List[CreditCard], monthly_spending: Dict[str, float]
) -> Tuple[LpProblem, Dict, Dict]:
    """Builds and returns the PuLP optimization problem."""
    prob = LpProblem("Unified_Card_Optimizer", LpMaximize)
    spend_vars, plan_vars, activated_bonus_vars, card_active_vars = _create_variables(
        cards
    )

    # --- Objective Function ---
    all_cashback = []
    for card in cards:
        total_spend = lpSum(
            spend_vars[card.name, cat.key] for cat in categories.values()
        )
        cashback_components: List[LpAffineExpression] = []
        if card.tiers:
            cashback_components = _add_tiered_cashback_logic(
                prob, card, total_spend, spend_vars, card_active_vars[card.name]
            )
        else:
            cashback_components = _add_regular_cashback_logic(card, spend_vars)

        if card.min_spend_for_cashback > 0:
            cashback_components = _gate_cashback_by_min_spend(
                prob,
                card,
                total_spend,
                card_active_vars[card.name],
                cashback_components,
            )

        all_cashback.extend(cashback_components)

    # Add lifestyle bonus to objective
    all_cashback.append(lpSum(activated_bonus_vars.values()))

    # Calculate total annual fees with new conditional logic
    total_annual_fees = []
    for card in cards:
        if (
            card.minimum_annual_spend_for_fee_waiver is not None
            and card.minimum_annual_spend_for_fee_waiver > 0
        ):
            fee_is_waived = LpVariable(f"FeeWaived_{card.name}", cat=LpBinary)
            prob += fee_is_waived <= card_active_vars[card.name]
            annual_spend_on_card = lpSum(
                spend_vars[card.name, cat.key] for cat in categories.values()
            ) * 12
            prob += (
                annual_spend_on_card
                >= card.minimum_annual_spend_for_fee_waiver
                - LARGE_NUMBER
                * (1 - fee_is_waived + (1 - card_active_vars[card.name])),
                f"Waived_Spend_Constraint_1_{card.name}",
            )
            prob += (
                annual_spend_on_card
                <= card.minimum_annual_spend_for_fee_waiver
                - 0.01
                + LARGE_NUMBER
                * (fee_is_waived + (1 - card_active_vars[card.name])),
                f"Waived_Spend_Constraint_2_{card.name}",
            )
            annual_fee_to_pay = (
                card.annual_fee_if_condition_not_met * card_active_vars[card.name]
                - (
                    card.annual_fee_if_condition_not_met - card.annual_fee
                )
                * fee_is_waived
            )
            total_annual_fees.append(annual_fee_to_pay)
        else:
            total_annual_fees.append(card.annual_fee * card_active_vars[card.name])

    # Final objective function: Net Annual Savings
    total_monthly_cashback = lpSum(all_cashback)
    prob += (
        (total_monthly_cashback * 12) - lpSum(total_annual_fees),
        "Total_Net_Annual_Savings",
    )

    # --- Constraints ---
    _add_constraints(
        prob, cards, monthly_spending, spend_vars, plan_vars, card_active_vars
    )

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
