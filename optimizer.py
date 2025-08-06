from typing import Dict, List, Tuple

import pandas as pd
from pulp import LpBinary, LpMaximize, LpProblem, LpVariable, lpSum

from models import CardCategory, CreditCard, LifestyleCard, TierCategory, categories


def _build_optimization_problem(
    cards: List[CreditCard], monthly_spending: Dict[str, float]
) -> Tuple[LpProblem, Dict, Dict]:
    """Builds and returns the PuLP optimization problem."""
    prob = LpProblem("Unified_Card_Optimizer", LpMaximize)

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

    # --- Objective Function ---
    all_cashback_components = []

    for card in cards:
        total_spend_on_card = lpSum(
            spend_vars[card.name, cat.key] for cat in categories.values()
        )
        M = 1000000  # A large number

        # Handle Tiered Cashback Cards (like SAIB)
        if card.tiers:
            tier_vars = LpVariable.dicts(
                f"TierChoice_{card.name}", (t.name for t in card.tiers), cat=LpBinary
            )
            prob += lpSum(tier_vars.values()) == 1, f"ChooseOneTier_{card.name}"

            for tier in card.tiers:
                y = tier_vars[tier.name]
                prob += total_spend_on_card >= tier.min_spend - M * (1 - y)
                if tier.max_spend != float("inf"):
                    prob += total_spend_on_card <= tier.max_spend + M * (1 - y)

                for cat in categories.values():
                    tier_cat_details = tier.categories.get(
                        cat, TierCategory(rate=tier.base_rate, cap=float("inf"))
                    )
                    cashback_for_cat_in_tier = (
                        spend_vars[card.name, cat.key] * tier_cat_details.rate
                    )
                    activated_cat_cashback = LpVariable(
                        f"Cashback_{card.name}_{tier.name}_{cat.key}", lowBound=0
                    )

                    prob += activated_cat_cashback <= M * y
                    prob += activated_cat_cashback <= cashback_for_cat_in_tier
                    if tier_cat_details.cap != float("inf"):
                        prob += cashback_for_cat_in_tier <= tier_cat_details.cap + M * (
                            1 - y
                        )

                    all_cashback_components.append(activated_cat_cashback)

        # Handle Cards with a Minimum Spend Requirement (like NBD)
        elif card.min_spend_for_cashback > 0:
            cashback_active = LpVariable(f"CashbackActive_{card.name}", cat=LpBinary)
            prob += total_spend_on_card >= card.min_spend_for_cashback - M * (
                1 - cashback_active
            )
            prob += (
                total_spend_on_card
                <= (card.min_spend_for_cashback - 0.01) + M * cashback_active
            )

            card_cashback = lpSum(
                spend_vars[card.name, cat.key]
                * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
                for cat in categories.values()
            )
            activated_cashback = LpVariable(
                f"ActivatedCashback_{card.name}", lowBound=0
            )
            prob += activated_cashback <= M * cashback_active
            prob += activated_cashback <= card_cashback
            all_cashback_components.append(activated_cashback)

        # Handle Regular and Lifestyle Cards
        else:
            base_cashback = lpSum(
                spend_vars[card.name, cat.key] * card.base_rate
                for cat in categories.values()
            )
            all_cashback_components.append(base_cashback)

            if not isinstance(card, LifestyleCard):
                for cat, card_cat in card.categories.items():
                    bonus = spend_vars[card.name, cat.key] * (
                        card_cat.rate - card.base_rate
                    )
                    all_cashback_components.append(bonus)

    all_cashback_components.append(lpSum(activated_bonus_vars.values()))

    total_monthly_cashback = lpSum(all_cashback_components)
    total_annual_fees = sum(c.annual_fee for c in cards)
    prob += (
        (total_monthly_cashback * 12) - total_annual_fees,
        "Total Net Annual Savings",
    )

    # --- Constraints ---
    for cat in categories.values():
        prob += (
            (
                lpSum(spend_vars[c.name, cat.key] for c in cards)
                == monthly_spending.get(cat.key, 0)
            ),
            f"Spend_Total_{cat.key}",
        )

    for card in cards:
        if card.tiers:
            continue

        if not isinstance(card, LifestyleCard) and card.monthly_cap != float("inf"):
            reg_card_cashback = lpSum(
                spend_vars[card.name, cat.key]
                * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
                for cat in categories.values()
            )
            prob += reg_card_cashback <= card.monthly_cap, f"MonthlyCap_{card.name}"

        for cat, card_cat in card.categories.items():
            if card_cat.cap != float("inf"):
                prob += (
                    (spend_vars[card.name, cat.key] * card_cat.rate) <= card_cat.cap,
                    f"CatCap_{card.name}_{cat.key}",
                )

        if card.grouped_monthly_caps:
            for i, (cap, cat_list) in enumerate(card.grouped_monthly_caps):
                prob += (
                    (
                        lpSum(
                            spend_vars[card.name, c.key]
                            * card.categories.get(
                                c, CardCategory(rate=card.base_rate)
                            ).rate
                            for c in cat_list
                        )
                        <= cap
                    ),
                    f"GroupCap_{card.name}_{i}",
                )

    if lifestyle_card:
        prob += lpSum(plan_vars.values()) == 1, "Select_One_Lifestyle_Plan"
        M = 1000000

        for plan in lifestyle_card.plans:
            potential_bonus = lpSum(
                spend_vars[lifestyle_card.name, category.key]
                * (card_category.rate - lifestyle_card.base_rate)
                for category_group in plan.categories_rate_cap
                for category, card_category in category_group.items()
            )
            prob += activated_bonus_vars[plan.name] <= M * plan_vars[plan.name]
            prob += activated_bonus_vars[plan.name] <= potential_bonus
            prob += activated_bonus_vars[plan.name] >= potential_bonus - M * (
                1 - plan_vars[plan.name]
            )

            for i, category_group in enumerate(plan.categories_rate_cap):
                cashback_in_group = lpSum(
                    spend_vars[lifestyle_card.name, cat.key] * card_cat.rate
                    for cat, card_cat in category_group.items()
                )
                cap_value = list(category_group.values())[0].cap
                if cap_value != float("inf"):
                    prob += (
                        (
                            cashback_in_group
                            <= cap_value + M * (1 - plan_vars[plan.name])
                        ),
                        f"PlanCap_{plan.name}_{i}",
                    )

    return prob, spend_vars, plan_vars


def _process_optimization_results(
    prob: LpProblem,
    cards: List[CreditCard],
    spend_vars: Dict,
    plan_vars: Dict,
) -> Tuple[pd.DataFrame, float, str]:
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

    return pd.DataFrame(results), prob.objective.value(), chosen_plan_name


def solve_optimization(
    cards: List[CreditCard], monthly_spending: Dict[str, float]
) -> Tuple[pd.DataFrame, float, str]:
    """Top-level function to solve the credit card optimization problem."""
    prob, spend_vars, plan_vars = _build_optimization_problem(cards, monthly_spending)
    prob.solve()

    if prob.status != 1:
        return None, None, None

    return _process_optimization_results(prob, cards, spend_vars, plan_vars)
