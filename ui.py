from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from models import CreditCard, LifestyleCard, categories


def setup_sidebar(t: dict, currency_symbol: str) -> Tuple[Dict[str, float], bool]:
    """Sets up the sidebar with sliders for monthly spending."""
    with st.sidebar:
        st.header(f"{t['sidebar_header']} ({currency_symbol})")
        default_spending = {
            "Dining": 1500, "Grocery": 2000, "Gas Station": 800, "Travel & Hotels": 1000,
            "Online Shopping (Local)": 750, "Pharmacy": 300, "Medical Care": 400, "Education": 500,
            "International Spend (Non-EUR)": 500, "Other Local Spend": 2000,
        }
        monthly_spending = {}
        for cat_obj in categories.values():
            monthly_spending[cat_obj.key] = st.slider(
                label=t[cat_obj.display_name],
                min_value=0, max_value=15000,
                value=default_spending.get(cat_obj.key, 0),
                step=50, format=f"{currency_symbol} %d",
            )

        total_monthly_spend = sum(monthly_spending.values())
        st.markdown("---")
        st.metric(
            label=t["total_spend_label"],
            value=f"{currency_symbol} {total_monthly_spend:,.0f}",
        )
        st.markdown("---")
        optimize_button = st.button(t["optimize_button"])
    return monthly_spending, optimize_button


def translate_plan_name(plan_name: str, t: dict) -> str:
    """Parses and translates a detailed plan name."""
    if not plan_name:
        return ""
    try:
        translated_parts = []
        tiers = plan_name.split(';')
        for tier in tiers:
            tier = tier.strip()
            rate_part, cat_part = tier.split(' on ')
            cat_names = [c.strip() for c in cat_part.split(',')]
            translated_cats = [t.get(name, name) for name in cat_names]
            translated_cats_str = ", ".join(translated_cats)
            translated_parts.append(f"**{rate_part}** {t['plan_on']} {translated_cats_str}")
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
        
        if not category_obj: continue

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
            {"Category": category_key, "Card": card_name, "Amount": amount, "Rate": effective_rate}
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


def display_charts(results_df: pd.DataFrame, cards: List[CreditCard], t: dict, currency_symbol: str):
    """Calculates and displays charts for spending and cashback using Plotly."""
    if results_df.empty:
        return

    st.markdown(f"### {t.get('charts_header', 'Visual Insights')}")

    # --- Chart 1: Spending per Card ---
    spending_per_card = results_df.groupby('Card')['Amount'].sum().reset_index()
    
    spending_fig = px.bar(
        spending_per_card,
        x='Card',
        y='Amount',
        title=t.get('spending_per_card_title', 'Total Spending per Card'),
        labels={'Card': t.get('card', 'Card'), 'Amount': f"{t.get('total_spending', 'Total Spending')} ({currency_symbol})"}
    )
    st.plotly_chart(spending_fig, use_container_width=True)

    # --- Chart 2: Cashback per Card ---
    results_df['Cashback'] = results_df.apply(
        lambda row: row['Amount'] * next(c for c in cards if c.name == row['Card']).categories.get(
            next(cat for cat in categories.values() if cat.key == row['Category']),
            type('obj', (object,), {'rate': next(c.base_rate for c in cards if c.name == row['Card'])})()
        ).rate,
        axis=1
    )
    
    cashback_per_card = results_df.groupby('Card')['Cashback'].sum().reset_index()

    cashback_fig = px.bar(
        cashback_per_card,
        x='Card',
        y='Cashback',
        title=t.get('cashback_per_card_title', 'Estimated Monthly Cashback per Card'),
        labels={'Card': t.get('card', 'Card'), 'Cashback': f"{t.get('total_cashback', 'Total Cashback')} ({currency_symbol})"}
    )
    st.plotly_chart(cashback_fig, use_container_width=True)


def display_results(results_df: pd.DataFrame, total_savings: float, chosen_plan: str, cards: List[CreditCard], t: dict, currency_symbol: str):
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
        results_df_display["Category"] = results_df_display["Category"].apply(
            lambda x: t.get(category_map_by_key[x].display_name, x)
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
    
    display_charts(results_df, cards, t, currency_symbol)

    st.markdown("---")
    priority_guide = generate_priority_guide(results_df, cards, chosen_plan, t)
    st.markdown(priority_guide)
    st.balloons()