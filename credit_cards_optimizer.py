from typing import Dict, List

import pandas as pd
import streamlit as st
from pulp import LpBinary, LpMaximize, LpProblem, LpVariable, lpSum

from cards.alrajhi import get_alrajhi_card
from cards.bsf import get_lifestyle_card
from cards.nbd import get_nbd_card
from cards.snb import get_snb_card
from models import CardCategory, CreditCard, LifestyleCard
from translations import TRANSLATIONS


def get_card_data() -> List[CreditCard]:
    """Initializes and returns a list of all credit card objects with their details."""

    return [
        get_snb_card(),
        get_alrajhi_card(),
        get_nbd_card(),
        get_lifestyle_card()

    ]


# --- PART 3: THE OPTIMIZATION MODEL ---
def solve_optimization(cards: List[CreditCard], monthly_spending: Dict[str, float]):
    prob = LpProblem("Unified_Card_Optimizer", LpMaximize)
    spend_vars = LpVariable.dicts(
        "Spend",
        ((c.name, cat) for c in cards for cat in UNIFIED_CATEGORIES),
        lowBound=0,
    )
    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    plan_vars, lifestyle_bonus_vars = {}, {}
    if lifestyle_card:
        plan_vars = LpVariable.dicts(
            "PlanChoice", (p.name for p in lifestyle_card.plans), cat=LpBinary
        )
        lifestyle_bonus_vars = LpVariable.dicts(
            "BonusCashback", (p.name for p in lifestyle_card.plans), lowBound=0
        )

    total_monthly_cashback, total_annual_fees = [], sum(c.annual_fee for c in cards)
    for card in cards:
        if not isinstance(card, LifestyleCard):
            total_monthly_cashback.append(
                lpSum(
                    spend_vars[card.name, cat]
                    * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
                    for cat in UNIFIED_CATEGORIES
                )
            )
    if lifestyle_card:
        total_monthly_cashback.append(
            lpSum(
                spend_vars[lifestyle_card.name, cat] * lifestyle_card.base_rate
                for cat in UNIFIED_CATEGORIES
            )
        )
        total_monthly_cashback.append(lpSum(lifestyle_bonus_vars.values()))
    prob += (
        lpSum(total_monthly_cashback) * 12
    ) - total_annual_fees, "Total Net Annual Savings"

    for cat in UNIFIED_CATEGORIES:
        prob += (
            lpSum(spend_vars[c.name, cat] for c in cards)
            == monthly_spending.get(cat, 0),
            f"Spend_{cat}",
        )

    for card in cards:
        if not isinstance(card, LifestyleCard) and card.monthly_cap != float("inf"):
            prob += (
                lpSum(
                    spend_vars[card.name, cat]
                    * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
                    for cat in UNIFIED_CATEGORIES
                )
                <= card.monthly_cap,
                f"MonthlyCap_{card.name}",
            )
        for cat_name, cat_details in card.categories.items():
            if cat_details.cap != float("inf"):
                prob += (
                    spend_vars[card.name, cat_name] * cat_details.rate
                    <= cat_details.cap,
                    f"CatCap_{card.name}_{cat_name}",
                )
        if card.annual_cap != float("inf"):
            monthly_cashback_for_card = None
            if isinstance(card, LifestyleCard):
                base_cashback = lpSum(
                    spend_vars[card.name, cat] * card.base_rate
                    for cat in UNIFIED_CATEGORIES
                )
                total_bonus_on_card = lpSum(
                    lifestyle_bonus_vars[p.name] for p in card.plans
                )
                monthly_cashback_for_card = base_cashback + total_bonus_on_card
            else:
                monthly_cashback_for_card = lpSum(
                    spend_vars[card.name, cat]
                    * card.categories.get(cat, CardCategory(rate=card.base_rate)).rate
                    for cat in UNIFIED_CATEGORIES
                )
            prob += (
                monthly_cashback_for_card * 12
            ) <= card.annual_cap, f"AnnualCap_{card.name}"
        if hasattr(card, "grouped_monthly_caps") and card.grouped_monthly_caps:
            for cap_value, categories in card.grouped_monthly_caps:
                prob += (
                    lpSum(
                        spend_vars[card.name, cat]
                        * card.categories.get(
                            cat, CardCategory(rate=card.base_rate)
                        ).rate
                        for cat in categories
                    )
                    <= cap_value,
                    f"GroupCap_{card.name}_{'_'.join(categories)}",
                )

    if lifestyle_card:
        prob += lpSum(plan_vars.values()) == 1, "ChooseOneLifestylePlan"
        M = 1000000
        for plan in lifestyle_card.plans:
            potential_bonus = lpSum(
                spend_vars[lifestyle_card.name, cat]
                * (plan.rate - lifestyle_card.base_rate)
                for cat in plan.categories
            )
            prob += (
                lifestyle_bonus_vars[plan.name]
                <= potential_bonus + M * (1 - plan_vars[plan.name]),
                f"BonusCalc_{plan.name}",
            )
            prob += (
                lifestyle_bonus_vars[plan.name] <= M * plan_vars[plan.name],
                f"BonusActivation_{plan.name}",
            )
            plan_category_cashback = lpSum(
                spend_vars[lifestyle_card.name, cat] * plan.rate
                for cat in plan.categories
            )
            prob += (
                plan_category_cashback <= plan.cap + M * (1 - plan_vars[plan.name]),
                f"LifestylePlanCap_{plan.name}",
            )

    prob.solve()
    if prob.status != 1:
        return None, None, None
    results = [
        {"Card": c.name, "Category": cat, "Amount": spend_vars[c.name, cat].varValue}
        for c in cards
        for cat in UNIFIED_CATEGORIES
        if spend_vars[c.name, cat].varValue is not None
        and spend_vars[c.name, cat].varValue > 0.01
    ]
    chosen_plan_name = ""
    if lifestyle_card:
        chosen_plan_name = next(
            (p_name for p_name, var in plan_vars.items() if var.varValue > 0.9), ""
        )
    return pd.DataFrame(results), prob.objective.value(), chosen_plan_name


# --- PART 4: HELPER FUNCTIONS FOR THE UI ---
def translate_plan_name(plan_name: str, t: dict) -> str:
    """Parses a plan name and translates it using the language dictionary."""
    if not plan_name:
        return ""
    try:
        parts = plan_name.split(" on ")
        rate_part = parts[0]
        cats_part = parts[1]
        categories = [c.strip() for c in cats_part.split("&")]
        translated_cats = [t.get(cat, cat) for cat in categories]
        join_word = f" {t['plan_and']} "
        translated_cats_str = join_word.join(translated_cats)
        return f"{rate_part} {t['plan_on']} {translated_cats_str}"
    except (IndexError, AttributeError):
        return plan_name


def generate_priority_guide(
    results_df: pd.DataFrame, cards: List[CreditCard], chosen_plan_name: str, t: dict
) -> str:
    if results_df.empty:
        return ""
    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    chosen_plan = (
        next((p for p in lifestyle_card.plans if p.name == chosen_plan_name), None)
        if lifestyle_card and chosen_plan_name
        else None
    )
    spending_details = []
    for _, row in results_df.iterrows():
        card, category, amount = row["Card"], row["Category"], row["Amount"]
        card_obj = next((c for c in cards if c.name == card), None)
        effective_rate = card_obj.base_rate
        if (
            isinstance(card_obj, LifestyleCard)
            and chosen_plan
            and category in chosen_plan.categories
        ):
            effective_rate = chosen_plan.rate
        elif category in card_obj.categories:
            effective_rate = card_obj.categories[category].rate
        spending_details.append(
            {
                "Category": category,
                "Card": card,
                "Amount": amount,
                "Rate": effective_rate,
            }
        )

    guide_text = f"### {t['priority_header']}\n\n{t['priority_description']}\n\n"
    has_priorities, df_details = False, pd.DataFrame(spending_details)
    currency_symbol = t["currency_symbol"]
    for category, group in df_details.groupby("Category"):
        if len(group) > 1:
            has_priorities = True
            guide_text += f"- **{t[category]}:**\n"
            sorted_group = group.sort_values("Rate", ascending=False)
            for i, (_, row) in enumerate(sorted_group.iterrows()):
                guide_text += f"  {i+1}. {t['priority_use']} **{row['Card']}** ({t['priority_at']} {row['Rate']:.1%}) {t['priority_for_first']} **{currency_symbol} {row['Amount']:,.2f}**.\n"
            guide_text += "\n"
    return guide_text if has_priorities else t["priority_none_needed"]


# --- PART 5: STREAMLIT USER INTERFACE ---
st.set_page_config(layout="wide", page_title="Credit Card Optimizer 💳")

if "lang" not in st.session_state:
    st.session_state.lang = "en"

lang_choice = st.sidebar.radio(
    "Language / اللغة",
    ["English", "العربية"],
    index=0 if st.session_state.lang == "en" else 1,
    horizontal=True,
)
st.session_state.lang = "ar" if lang_choice == "العربية" else "en"
t = TRANSLATIONS[st.session_state.lang]

if st.session_state.lang == "ar":
    st.markdown(
        """<style>
    body { direction: rtl; }
    .stRadio [role=radiogroup]{ flex-direction: row-reverse; }
    div[data-testid="stSlider"] > div[data-baseweb="slider"] > div { direction: ltr; }
    </style>""",
        unsafe_allow_html=True,
    )

st.title(t["title"])
st.markdown(t["description"])
st.markdown("---")

cards = get_card_data()
currency_symbol = t["currency_symbol"]

with st.sidebar:
    st.header(f"{t['sidebar_header']} ({currency_symbol})")
    default_spending = {
        "Dining": 1500,
        "Grocery": 2000,
        "Gas Station": 800,
        "Travel & Hotels": 1000,
        "Online Shopping (Local)": 750,
        "Pharmacy": 300,
        "Medical Care": 400,
        "Education": 500,
        "International Spend (Non-EUR)": 500,
        "Other Local Spend": 2000,
    }
    monthly_spending = {
        cat: st.slider(
            label=t[cat],
            min_value=0,
            max_value=15000,
            value=default_spending.get(cat, 0),
            step=50,
            format=f"{currency_symbol} %d",
        )
        for cat in UNIFIED_CATEGORIES
    }
    total_monthly_spend = sum(monthly_spending.values())
    st.markdown("---")
    st.metric(
        label=t["total_spend_label"],
        value=f"{currency_symbol} {total_monthly_spend:,.0f}",
    )
    st.markdown("---")
    optimize_button = st.button(t["optimize_button"])

if optimize_button:
    if sum(monthly_spending.values()) == 0:
        st.warning(t["warning_no_spend"])
    else:
        with st.spinner(t["spinner_text"]):
            results_df, total_savings, chosen_plan = solve_optimization(
                cards, monthly_spending
            )
        if results_df is None:
            st.error(t["error_no_solution"])
        else:
            st.success(t["success_title"])
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label=t["metric_savings"],
                    value=f"{currency_symbol} {total_savings:,.2f}",
                    help=t["metric_savings_help"],
                )
            with col2:
                if chosen_plan:
                    translated_plan = translate_plan_name(chosen_plan, t)
                    st.metric(
                        label=t["metric_plan"],
                        value=translated_plan,
                        help=t["metric_plan_help"],
                    )
            st.markdown(f"### {t['results_header']}")
            st.markdown(t["results_description"])
            if not results_df.empty:
                results_df_display = results_df.copy()
                results_df_display["Category"] = results_df_display["Category"].apply(
                    lambda x: t.get(x, x)
                )
                amount_col_name = f"Amount ({currency_symbol})"
                results_df_display[amount_col_name] = results_df_display[
                    "Amount"
                ].apply(lambda x: f"{currency_symbol} {x:,.2f}")
                pivot_df = results_df_display.pivot(
                    index="Category", columns="Card", values=amount_col_name
                ).fillna(" - ")

                card_links = {card.name: card.reference_link for card in cards}
                new_columns = [
                    (
                        f'<a href="{card_links.get(col, "#")}" target="_blank" style="color: inherit; text-decoration: none;">{col}</a>'
                        if col in card_links
                        else col
                    )
                    for col in pivot_df.columns
                ]
                pivot_df.columns = new_columns

                st.markdown(pivot_df.to_html(escape=False), unsafe_allow_html=True)
            else:
                st.write(t["results_no_spend"])
            st.markdown("---")
            priority_guide = generate_priority_guide(results_df, cards, chosen_plan, t)
            st.markdown(priority_guide)
            st.balloons()

st.markdown("---")
st.info(t["footer_info"], icon="ℹ️")
