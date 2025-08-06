
import streamlit as st

from cards.alrajhi import get_alrajhi_card
from cards.bsf import get_lifestyle_card
from cards.nbd import get_nbd_card
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

    cards = [
        get_snb_card(),
        get_alrajhi_card(),
        get_nbd_card(),
        get_lifestyle_card(),
        get_saib_card(),
    ]
    currency_symbol = t["currency_symbol"]

    monthly_spending, optimize_button = setup_sidebar(t, currency_symbol)

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
                display_results(results_df, total_savings, chosen_plan, cards, t, currency_symbol)

    st.markdown("---")
    st.info(t["footer_info"], icon="ℹ️")


if __name__ == "__main__":
    main()