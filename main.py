"""
Main script for the Credit Card Optimizer Streamlit application.

This script sets up the user interface, handles user input, and
calls the optimization logic to find the best credit card combination.
"""

import streamlit as st

from cards.alrajhi import get_alrajhi_card
from cards.bsf import get_lifestyle_card
from cards.nayfat import get_nayfat_card
from cards.nbd import get_nbd_card
from cards.sabb import get_sabb_card
from cards.saib import get_saib_card
from cards.snb import get_snb_card
from optimizer import solve_optimization
from translations import TRANSLATIONS
from ui import display_results, setup_sidebar


def main():
    """Main function to run the Streamlit application."""
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

    # --- FINAL CSS FIX ---
    # This selector is highly specific to override Streamlit's defaults.
    # It targets the text span inside the multiselect component in the sidebar.
    st.markdown(
        """<style>
    div[data-testid="stSidebar"] div[data-baseweb="select"]
    div[role="listbox"] div[data-baseweb="tag"] > span {
        font-size: 6px !important;
    }

    /* --- Language Specific Styles --- */
    .stRadio[role=radiogroup]{
        flex-direction: row-reverse;
    }
    div[data-testid="stSlider"] > div[data-baseweb="slider"] > div {
        direction: ltr;
    }
    </style>""",
        unsafe_allow_html=True,
    )

    if st.session_state.lang == "ar":
        st.markdown(
            "<style>body { direction: rtl; }</style>",
            unsafe_allow_html=True,
        )

    st.title(t["title"])
    st.markdown(t["description"])
    st.markdown("---")

    all_cards = [
        get_snb_card(),
        get_alrajhi_card(),
        get_nbd_card(),
        get_lifestyle_card(),
        get_saib_card(),
        get_sabb_card(),
        get_nayfat_card()
    ]
    currency_symbol = t["currency_symbol"]

    monthly_spending, optimize_button, selected_card_names = setup_sidebar(
        t, currency_symbol, all_cards
    )

    if optimize_button:
        if sum(monthly_spending.values()) == 0:
            st.warning(t["warning_no_spend"])
        else:
            with st.spinner(t["spinner_text"]):
                selected_cards = [
                    card for card in all_cards if card.name in selected_card_names
                ]
                optimization_result = solve_optimization(
                    selected_cards, {k: float(v) for k, v in monthly_spending.items()}
                )
            if optimization_result is None:
                st.error(t["error_no_solution"])
            else:
                display_results(
                    optimization_result,
                    selected_cards,
                    t,
                    currency_symbol,
                )

    st.markdown("---")
    st.info(t["footer_info"], icon="ℹ️")


if __name__ == "__main__":
    main()
