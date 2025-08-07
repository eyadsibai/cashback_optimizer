"""
This module handles the user interface components of the Streamlit application,
including the sidebar setup, results display, and chart generation.
"""

from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from models import CreditCard, LifestyleCard, OptimizationResult, categories

def _setup_spending_inputs(t: dict, currency_symbol: str) -> Dict[str, int]:
    """Creates and returns the spending input fields in the sidebar."""
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
    monthly_spending = {}
    for cat_obj in categories.values():
        monthly_spending[cat_obj.key] = st.number_input(
            label=t[cat_obj.display_name],
            min_value=0,
            max_value=100000,
            value=default_spending.get(cat_obj.key, 0),
            step=50,
            key=cat_obj.key,
        )
    return monthly_spending





def _setup_card_selection(t: dict, cards: List[CreditCard]) -> List[str]:
    """Creates and returns the card selection checkboxes."""
    st.subheader(t.get("card_selection_header", "Select Credit Cards"))
    selected_card_names = []
    for card in cards:
        if st.checkbox(card.name, value=True, key=f"card_{card.name}"):
            selected_card_names.append(card.name)
    if len(selected_card_names) != len(cards):
        st.warning(t.get("select_all_warning", "For max savings, select all cards."))
    return selected_card_names


def setup_sidebar(
    t: dict, currency_symbol: str, cards: List[CreditCard]
) -> Tuple[Dict[str, int], bool, List[str]]:
    """Sets up the sidebar with input fields for monthly spending."""
    with st.sidebar:
        monthly_spending = _setup_spending_inputs(t, currency_symbol)
        st.markdown("---")
        selected_card_names = _setup_card_selection(t, cards)
        st.markdown("---")
        total_monthly_spend = sum(monthly_spending.values())
        st.metric(
            label=t["total_spend_label"],
            value=f"{currency_symbol} {total_monthly_spend:,.0f}",
        )
        st.markdown("---")
        optimize_button = st.button(t["optimize_button"])

    return monthly_spending, optimize_button, selected_card_names


def translate_plan_name(plan_name: str, t: dict) -> str:
    """Parses and translates a detailed plan name."""
    if not plan_name:
        return ""
    try:
        parts = []
        for tier in plan_name.split(";"):
            rate_part, cat_part = tier.strip().split(" on ")
            cat_names = [c.strip() for c in cat_part.split(",")]
            translated_cats = [t.get(name, name) for name in cat_names]
            parts.append(f"**{rate_part}** {t['plan_on']} {', '.join(translated_cats)}")
        return "<br>".join(parts)
    except (ValueError, IndexError):
        return plan_name


def _get_spending_details(
    results_df: pd.DataFrame, cards: List[CreditCard], chosen_plan_name: str
) -> pd.DataFrame:
    """Calculates effective rates and returns a detailed spending DataFrame."""
    category_map = {cat.key: cat for cat in categories.values()}
    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    chosen_plan = (
        next((p for p in lifestyle_card.plans if p.name == chosen_plan_name), None)
        if lifestyle_card and chosen_plan_name
        else None
    )

    details = []
    for _, row in results_df.iterrows():
        card = next((c for c in cards if c.name == row["Card"]), None)
        cat = category_map.get(row["Category"])
        if not (card and cat):
            continue

        rate = 0.0
        if card:
            rate = card.base_rate
            if card == lifestyle_card and chosen_plan:
                for group in chosen_plan.categories_rate_cap:
                    if cat in group:
                        rate = group[cat].rate
                        break
            elif cat in card.categories:
                rate = card.categories[cat].rate

        details.append(
            {
                "Category": cat.key,
                "Card": card.name,
                "Amount": row["Amount"],
                "Rate": rate,
            }
        )
    return pd.DataFrame(details)


def generate_priority_guide(
    results_df: pd.DataFrame, cards: List[CreditCard], chosen_plan_name: str, t: dict
) -> str:
    """Generates a markdown guide for spending priorities."""
    if results_df.empty:
        return ""

    df_details = _get_spending_details(results_df, cards, chosen_plan_name)
    if df_details.empty:
        return t["priority_none_needed"]

    guide = [f"### {t['priority_header']}", t["priority_description"]]
    has_priorities = False
    currency = t["currency_symbol"]
    cat_map = {cat.key: cat for cat in categories.values()}

    for cat_key, group in df_details.groupby("Category"):
        if len(group) > 1:
            has_priorities = True
            display_name = t.get(cat_map[cat_key].display_name, cat_key)
            guide.append(f"- **{display_name}:**")
            sorted_group = pd.DataFrame(group).sort_values("Rate", ascending=False)
            for i, (_, row) in enumerate(sorted_group.iterrows()):
                guide.append(
                    f"  {i+1}. {t['priority_use']} **{row['Card']}** "
                    f"({t['priority_at']} {row['Rate']:.1%}) "
                    f"{t['priority_for_first']} **{currency} {row['Amount']:,.2f}**."
                )
            guide.append("")

    return "\n".join(guide) if has_priorities else t["priority_none_needed"]


def display_charts(results_df: pd.DataFrame, t: dict, currency_symbol: str):
    """Displays a combined chart for spending and cashback."""
    if results_df.empty:
        return

    st.markdown(f"### {t.get('charts_header', 'Visual Insights')}")

    results_df["Monthly Cashback"] = results_df["Amount"] * results_df["Rate"]
    monthly_spending = results_df.groupby("Card")["Amount"].sum()
    monthly_cashback = results_df.groupby("Card")["Monthly Cashback"].sum()

    chart_data = pd.DataFrame(
        {
            "Card": monthly_spending.index,
            "Monthly Spending": monthly_spending.values,
            "Monthly Cashback": monthly_cashback.values,
            "Yearly Spending": monthly_spending.values.to_numpy() * 12,
            "Yearly Cashback": monthly_cashback.values.to_numpy() * 12,
        }
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=t.get("spending"),
            x=chart_data["Card"],
            y=chart_data["Monthly Spending"],
        )
    )
    fig.add_trace(
        go.Bar(
            name=t.get("cashback"),
            x=chart_data["Card"],
            y=chart_data["Monthly Cashback"],
        )
    )
    fig.add_trace(
        go.Bar(
            name=t.get("spending"),
            x=chart_data["Card"],
            y=chart_data["Yearly Spending"],
            visible=False,
        )
    )
    fig.add_trace(
        go.Bar(
            name=t.get("cashback"),
            x=chart_data["Card"],
            y=chart_data["Yearly Cashback"],
            visible=False,
        )
    )

    fig.update_layout(
        title=t.get("combined_chart_title", "Spending vs. Cashback"),
        barmode="group",
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "active": 0,
                "x": 0.57,
                "y": 1.2,
                "buttons": [
                    {
                        "label": t.get("monthly"),
                        "method": "update",
                        "args": [
                            {"visible": [True, True, False, False]},
                            {"title": t.get("combined_chart_title_monthly")},
                        ],
                    },
                    {
                        "label": t.get("yearly"),
                        "method": "update",
                        "args": [
                            {"visible": [False, False, True, True]},
                            {"title": t.get("combined_chart_title_yearly")},
                        ],
                    },
                ],
            }
        ],
        yaxis_title=f"{t.get('amount')} ({currency_symbol})",
    )
    st.plotly_chart(fig, use_container_width=True)


def _display_results_header(total_savings, chosen_plan, t, currency_symbol):
    """Displays the header section of the results."""
    st.success(t["success_title"])
    col1, col2 = st.columns(2)
    col1.metric(
        label=t["metric_savings"],
        value=f"{currency_symbol} {total_savings:,.2f}",
        help=t["metric_savings_help"],
    )
    if chosen_plan:
        with col2:
            st.markdown(f"**{t['metric_plan']}**")
            st.markdown(translate_plan_name(chosen_plan, t), unsafe_allow_html=True)
            st.caption(t["metric_plan_help"])


def _display_allocation_table(results_df, cards, t, currency_symbol):
    """Displays the spending allocation pivot table."""
    st.markdown(f"#### {t.get('allocation_header', 'Spending Allocation')}")
    category_map = {cat.key: cat for cat in categories.values()}
    df = results_df.copy()
    df["Category"] = df["Category"].apply(
        lambda k: t.get(category_map[k].display_name, k)
    )
    amount_col = f"{t.get('amount_col', 'Amount')} ({currency_symbol})"
    df[amount_col] = df["Amount"].apply(lambda x: f"{currency_symbol} {x:,.2f}")

    pivot = df.pivot_table(
        index="Category", columns="Card", values=amount_col, aggfunc="first"
    ).fillna(" - ")

    card_links = {c.name: c.reference_link for c in cards}
    pivot.columns = pd.Index(
        [
            f'<a href="{card_links.get(col, "#")}" target="_blank">{col}</a>'
            for col in pivot.columns
        ]
    )
    st.markdown(pivot.to_html(escape=False), unsafe_allow_html=True)
    st.write("")


def _display_savings_breakdown(results_df, t, currency_symbol):
    """Displays the savings breakdown table."""
    st.markdown(f"#### {t.get('savings_breakdown_header', 'Savings Breakdown')}")
    category_map = {cat.key: cat for cat in categories.values()}
    df = results_df.copy()
    df["Category"] = df["Category"].apply(
        lambda k: t.get(category_map[k].display_name, k)
    )
    df["Savings"] = df["Amount"] * df["Rate"]
    savings_per_cat = df.groupby("Category")["Savings"].sum().reset_index()
    savings_per_cat["Savings"] = savings_per_cat["Savings"].apply(
        lambda x: f"{currency_symbol} {x:,.2f}"
    )
    st.dataframe(savings_per_cat, use_container_width=True)


def display_results(
    result: OptimizationResult,
    cards: List[CreditCard],
    t: dict,
    currency_symbol: str,
):
    """Displays the optimization results on the main page."""
    _display_results_header(
        result.total_savings, result.chosen_plan, t, currency_symbol
    )

    st.markdown(f"### {t['results_header']}")
    st.markdown(t["results_description"])

    if result.results_df.empty:
        st.write(t["results_no_spend"])
        return

    # Get detailed spending info with correct rates
    detailed_df = _get_spending_details(result.results_df, cards, result.chosen_plan)

    _display_allocation_table(detailed_df, cards, t, currency_symbol)
    _display_savings_breakdown(detailed_df, t, currency_symbol)

    st.markdown("---")
    display_charts(detailed_df, t, currency_symbol)

    st.markdown("---")
    priority_guide = generate_priority_guide(
        result.results_df, cards, result.chosen_plan, t
    )
    st.markdown(priority_guide)
    st.balloons()
