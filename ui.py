from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from models import CreditCard, LifestyleCard, categories


def setup_sidebar(
    t: dict, currency_symbol: str, cards: List[CreditCard]
) -> Tuple[Dict[str, float], bool, List[str]]:
    """Sets up the sidebar with sliders for monthly spending."""
    with st.sidebar:
        st.header(f"{t['sidebar_header']} ({currency_symbol})")

        # Spending Sliders
        default_spending = {
            "Dining": 1500, "Grocery": 2000, "Gas Station": 800, "Travel & Hotels": 1000,
            "Online Shopping (Local)": 750, "Pharmacy": 300, "Medical Care": 400,
            "Education": 500, "International Spend (Non-EUR)": 500, "Other Local Spend": 2000,
        }
        monthly_spending = {}
        for cat_obj in categories.values():
            monthly_spending[cat_obj.key] = st.slider(
                label=t[cat_obj.display_name], min_value=0, max_value=15000,
                value=default_spending.get(cat_obj.key, 0), step=50,
                format=f"{currency_symbol} %d",
            )
        st.markdown("---")

        # --- REPLACEMENT: Use Checkboxes instead of Multiselect ---
        st.subheader(t.get("card_selection_header", "Select Credit Cards"))
        selected_card_names = []
        for card in cards:
            # Create a checkbox for each card, checked by default
            if st.checkbox(card.name, value=True, key=f"card_{card.name}"):
                selected_card_names.append(card.name)

        if len(selected_card_names) != len(cards):
            st.warning(
                "Warning: For maximum savings, it's recommended to select all credit cards."
            )
        # --- End of Replacement ---

        total_monthly_spend = sum(monthly_spending.values())
        st.markdown("---")
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
        translated_parts = []
        tiers = plan_name.split(";")
        for tier in tiers:
            tier = tier.strip()
            rate_part, cat_part = tier.split(" on ")
            cat_names = [c.strip() for c in cat_part.split(",")]
            translated_cats = [t.get(name, name) for name in cat_names]
            translated_cats_str = ", ".join(translated_cats)
            translated_parts.append(
                f"**{rate_part}** {t['plan_on']} {translated_cats_str}"
            )
        return "<br>".join(translated_parts)
    except (ValueError, IndexError):
        return plan_name


def generate_priority_guide(
    results_df: pd.DataFrame, cards: List[CreditCard], chosen_plan_name: str, t: dict
) -> str:
    """Generates a markdown guide for spending priorities."""
    if results_df.empty:
        return ""

    category_map = {cat.key: cat for cat in categories.values()}
    lifestyle_card = next((c for c in cards if isinstance(c, LifestyleCard)), None)
    chosen_plan = (
        next((p for p in lifestyle_card.plans if p.name == chosen_plan_name), None)
        if lifestyle_card and chosen_plan_name
        else None
    )

    spending_details = []
    for _, row in results_df.iterrows():
        card_name, category_key, amount = row["Card"], row["Category"], row["Amount"]
        card_obj = next((c for c in cards if c.name == card_name), None)
        category_obj = category_map.get(category_key)

        if not category_obj:
            continue

        effective_rate = card_obj.base_rate
        if card_obj == lifestyle_card and chosen_plan:
            is_in_plan = False
            for group in chosen_plan.categories_rate_cap:
                if category_obj in group:
                    effective_rate = group[category_obj].rate
                    is_in_plan = True
                    break
            if not is_in_plan:
                effective_rate = lifestyle_card.base_rate
        elif category_obj in card_obj.categories:
            effective_rate = card_obj.categories[category_obj].rate

        spending_details.append(
            {
                "Category": category_key,
                "Card": card_name,
                "Amount": amount,
                "Rate": effective_rate,
            }
        )

    guide_text = f"### {t['priority_header']}\n\n{t['priority_description']}\n\n"
    has_priorities = False
    df_details = pd.DataFrame(spending_details)
    currency_symbol = t["currency_symbol"]

    for category_key, group in df_details.groupby("Category"):
        if len(group) > 1:
            has_priorities = True
            category_display_name = t.get(category_map[category_key].display_name, category_key)
            guide_text += f"- **{category_display_name}:**\n"
            sorted_group = group.sort_values("Rate", ascending=False)
            for i, (_, row) in enumerate(sorted_group.iterrows()):
                guide_text += f"  {i+1}. {t['priority_use']} **{row['Card']}** ({t['priority_at']} {row['Rate']:.1%}) {t['priority_for_first']} **{currency_symbol} {row['Amount']:,.2f}**.\n"
            guide_text += "\n"

    return guide_text if has_priorities else t["priority_none_needed"]


def display_charts(
    results_df: pd.DataFrame, cards: List[CreditCard], t: dict, currency_symbol: str
):
    """Calculates and displays a combined chart for spending and cashback with a period toggle."""
    if results_df.empty:
        return

    st.markdown(f"### {t.get('charts_header', 'Visual Insights')}")

    # --- Data Preparation ---
    category_map = {cat.key: cat for cat in categories.values()}

    def get_effective_rate(row):
        card_obj = next((c for c in cards if c.name == row["Card"]), None)
        category_obj = category_map.get(row["Category"])
        # This simplified rate calculation is for visualization; the optimizer used the full logic.
        return card_obj.categories.get(
            category_obj, type("obj", (object,), {"rate": card_obj.base_rate})()
        ).rate

    results_df["Rate"] = results_df.apply(get_effective_rate, axis=1)
    results_df["Monthly Cashback"] = results_df["Amount"] * results_df["Rate"]

    monthly_spending = results_df.groupby("Card")["Amount"].sum()
    monthly_cashback = results_df.groupby("Card")["Monthly Cashback"].sum()

    chart_data = pd.DataFrame(
        {
            "Card": monthly_spending.index,
            "Monthly Spending": monthly_spending.values,
            "Monthly Cashback": monthly_cashback.values,
            "Yearly Spending": monthly_spending.values * 12,
            "Yearly Cashback": monthly_cashback.values * 12,
        }
    )

    # --- Chart Creation with Plotly Graph Objects ---
    fig = go.Figure()

    # Add traces for Monthly data (visible by default)
    fig.add_trace(
        go.Bar(
            name=t.get("spending", "Spending"),
            x=chart_data["Card"],
            y=chart_data["Monthly Spending"],
            marker_color="#1f77b4",
        )
    )
    fig.add_trace(
        go.Bar(
            name=t.get("cashback", "Cashback"),
            x=chart_data["Card"],
            y=chart_data["Monthly Cashback"],
            marker_color="#2ca02c",
        )
    )

    # Add traces for Yearly data (initially invisible)
    fig.add_trace(
        go.Bar(
            name=t.get("spending", "Spending"),
            x=chart_data["Card"],
            y=chart_data["Yearly Spending"],
            visible=False,
            marker_color="#1f77b4",
        )
    )
    fig.add_trace(
        go.Bar(
            name=t.get("cashback", "Cashback"),
            x=chart_data["Card"],
            y=chart_data["Yearly Cashback"],
            visible=False,
            marker_color="#2ca02c",
        )
    )

    # --- Add Buttons to Switch Views ---
    fig.update_layout(
        title=t.get("combined_chart_title", "Spending vs. Cashback by Card"),
        barmode="group",
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                x=0.57,
                y=1.2,
                buttons=list(
                    [
                        dict(
                            label=t.get("monthly", "Monthly"),
                            method="update",
                            args=[
                                {"visible": [True, True, False, False]},
                                {
                                    "title": t.get(
                                        "combined_chart_title_monthly",
                                        "Monthly Spending vs. Cashback",
                                    )
                                },
                            ],
                        ),
                        dict(
                            label=t.get("yearly", "Yearly"),
                            method="update",
                            args=[
                                {"visible": [False, False, True, True]},
                                {
                                    "title": t.get(
                                        "combined_chart_title_yearly",
                                        "Yearly Spending vs. Cashback",
                                    )
                                },
                            ],
                        ),
                    ]
                ),
            )
        ],
    )

    fig.update_yaxes(title_text=f"{t.get('amount', 'Amount')} ({currency_symbol})")

    st.plotly_chart(fig, use_container_width=True)


def display_results(
    results_df: pd.DataFrame,
    total_savings: float,
    chosen_plan: str,
    cards: List[CreditCard],
    t: dict,
    currency_symbol: str,
):
    """Displays the optimization results on the main page."""
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
            st.markdown(f"**{t['metric_plan']}**")
            translated_plan = translate_plan_name(chosen_plan, t)
            st.markdown(translated_plan, unsafe_allow_html=True)
            st.caption(t["metric_plan_help"])

    st.markdown(f"### {t['results_header']}")
    st.markdown(t["results_description"])

    if not results_df.empty:
        category_map_by_key = {cat.key: cat for cat in categories.values()}
        results_df_display = results_df.copy()
        
        # Ensure 'Rate' column exists for savings calculation
        if 'Rate' not in results_df_display.columns:
            # This is a fallback; the rate should ideally be in the df from the optimizer
            category_map = {cat.key: cat for cat in categories.values()}
            def get_effective_rate(row):
                card_obj = next((c for c in cards if c.name == row['Card']), None)
                category_obj = category_map.get(row['Category'])
                # Simplified rate calculation, assuming no lifestyle card complexity for display
                return card_obj.categories.get(category_obj, type('obj', (object,), {'rate': card_obj.base_rate})()).rate
            results_df_display['Rate'] = results_df_display.apply(get_effective_rate, axis=1)

        results_df_display["Category"] = results_df_display["Category"].apply(
            lambda x: t.get(category_map_by_key[x].display_name, x)
        )
        amount_col_name = f"{t.get('amount_col', 'Amount')} ({currency_symbol})"
        results_df_display[amount_col_name] = results_df_display["Amount"].apply(
            lambda x: f"{currency_symbol} {x:,.2f}"
        )
        savings_col_name = f"{t.get('savings_col', 'Savings')} ({currency_symbol})"
        results_df_display[savings_col_name] = (
            results_df_display["Amount"] * results_df_display["Rate"]
        ).apply(lambda x: f"{currency_symbol} {x:,.2f}")
        
        # Create a pivot table for spending allocation
        st.markdown(f"#### {t.get('allocation_header', 'Spending Allocation')}")
        pivot_df_amount = results_df_display.pivot_table(
            index="Category", columns="Card", values=amount_col_name, aggfunc='first'
        ).fillna(" - ")

        card_links = {card.name: card.reference_link for card in cards}
        new_columns_amount = [
            (
                f'<a href="{card_links.get(col, "#")}" target="_blank" style="color: inherit; text-decoration: none; font-weight: bold;">{col}</a>'
            )
            for col in pivot_df_amount.columns
        ]
        pivot_df_amount.columns = new_columns_amount
        st.markdown(pivot_df_amount.to_html(escape=False), unsafe_allow_html=True)
        st.write("") 

        # Create a table for savings per category
        st.markdown(f"#### {t.get('savings_breakdown_header', 'Savings Breakdown')}")
        
        # Ensure we're summing numeric savings values correctly
        results_df_display['NumericSavings'] = results_df_display["Amount"] * results_df_display["Rate"]
        savings_per_category = results_df_display.groupby("Category")['NumericSavings'].sum().reset_index()
        savings_per_category = savings_per_category.rename(columns={"NumericSavings": "Total Savings"})
        savings_per_category["Total Savings"] = savings_per_category["Total Savings"].apply(lambda x: f"{currency_symbol} {x:,.2f}")
        
        st.dataframe(savings_per_category, use_container_width=True)

    else:
        st.write(t["results_no_spend"])
    st.markdown("---")

    display_charts(results_df, cards, t, currency_symbol)

    st.markdown("---")
    priority_guide = generate_priority_guide(results_df, cards, chosen_plan, t)
    st.markdown(priority_guide)
    st.balloons()