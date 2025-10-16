"""Tests for ui.py helper functions."""

import pathlib
import sys

import pytest
import pandas as pd

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from models import (
    CardCategory,
    CreditCard,
    LifestyleCard,
    LifestylePlan,
    OptimizationResult,
    categories,
)
from ui import (
    translate_plan_name,
    _get_spending_details,
    generate_priority_guide,
)
from translations import TRANSLATIONS


class TestTranslatePlanName:
    """Tests for translate_plan_name function."""

    def test_translate_empty_plan_name(self):
        """Test translating an empty plan name."""
        result = translate_plan_name("", TRANSLATIONS["en"])
        assert result == ""

    def test_translate_plan_name_english(self):
        """Test translating a plan name to English."""
        plan_name = "10% on Dining; 3% on Grocery, Education"
        result = translate_plan_name(plan_name, TRANSLATIONS["en"])
        assert "10%" in result
        assert "Dining" in result or "مطاعم ومقاهي" not in result

    def test_translate_plan_name_arabic(self):
        """Test translating a plan name to Arabic."""
        plan_name = "10% on Dining; 3% on Grocery, Education"
        result = translate_plan_name(plan_name, TRANSLATIONS["ar"])
        assert "10%" in result

    def test_translate_plan_name_invalid_format(self):
        """Test translating an invalid plan name format."""
        plan_name = "Invalid Format"
        result = translate_plan_name(plan_name, TRANSLATIONS["en"])
        assert result == plan_name


class TestGetSpendingDetails:
    """Tests for _get_spending_details function."""

    def test_get_spending_details_empty_df(self):
        """Test _get_spending_details with empty DataFrame."""
        results_df = pd.DataFrame()
        cards = []
        result = _get_spending_details(results_df, cards, "")
        assert result.empty

    def test_get_spending_details_basic(self):
        """Test _get_spending_details with basic data."""
        results_df = pd.DataFrame(
            {
                "Card": ["Card A"],
                "Category": ["Dining"],
                "Amount": [100.0],
            }
        )
        card = CreditCard(
            name="Card A",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.02,
        )
        result = _get_spending_details(results_df, [card], "")
        assert len(result) == 1
        assert result.iloc[0]["Card"] == "Card A"
        assert result.iloc[0]["Amount"] == 100.0
        assert result.iloc[0]["Rate"] == 0.02

    def test_get_spending_details_with_category_rate(self):
        """Test _get_spending_details with category-specific rate."""
        results_df = pd.DataFrame(
            {
                "Card": ["Card A"],
                "Category": ["Dining"],
                "Amount": [100.0],
            }
        )
        card = CreditCard(
            name="Card A",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.01,
            categories={categories["dining"]: CardCategory(rate=0.05)},
        )
        result = _get_spending_details(results_df, [card], "")
        assert len(result) == 1
        assert result.iloc[0]["Rate"] == 0.05

    def test_get_spending_details_with_lifestyle_card(self):
        """Test _get_spending_details with LifestyleCard."""
        results_df = pd.DataFrame(
            {
                "Card": ["Lifestyle"],
                "Category": ["Dining"],
                "Amount": [100.0],
            }
        )
        plan = LifestylePlan(
            name="Plan 1",
            categories_rate_cap=[{categories["dining"]: CardCategory(rate=0.10, cap=250)}],
        )
        card = LifestyleCard(
            name="Lifestyle",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.01,
            plans=[plan],
        )
        result = _get_spending_details(results_df, [card], "Plan 1")
        assert len(result) == 1
        assert result.iloc[0]["Rate"] == 0.10

    def test_get_spending_details_multiple_cards(self):
        """Test _get_spending_details with multiple cards."""
        results_df = pd.DataFrame(
            {
                "Card": ["Card A", "Card B"],
                "Category": ["Dining", "Grocery"],
                "Amount": [100.0, 200.0],
            }
        )
        card_a = CreditCard(
            name="Card A", reference_link="http://test.com", annual_fee=0, base_rate=0.02
        )
        card_b = CreditCard(
            name="Card B", reference_link="http://test.com", annual_fee=0, base_rate=0.03
        )
        result = _get_spending_details(results_df, [card_a, card_b], "")
        assert len(result) == 2


class TestGeneratePriorityGuide:
    """Tests for generate_priority_guide function."""

    def test_generate_priority_guide_empty_df(self):
        """Test generate_priority_guide with empty DataFrame."""
        results_df = pd.DataFrame()
        result = generate_priority_guide(results_df, [], "", TRANSLATIONS["en"])
        assert result == ""

    def test_generate_priority_guide_single_card_per_category(self):
        """Test generate_priority_guide when each category has only one card."""
        results_df = pd.DataFrame(
            {
                "Card": ["Card A", "Card B"],
                "Category": ["Dining", "Grocery"],
                "Amount": [100.0, 200.0],
            }
        )
        card_a = CreditCard(
            name="Card A", reference_link="http://test.com", annual_fee=0, base_rate=0.02
        )
        card_b = CreditCard(
            name="Card B", reference_link="http://test.com", annual_fee=0, base_rate=0.03
        )
        result = generate_priority_guide(
            results_df, [card_a, card_b], "", TRANSLATIONS["en"]
        )
        assert "no special priority" in result.lower() or "none needed" in result.lower()

    def test_generate_priority_guide_multiple_cards_per_category(self):
        """Test generate_priority_guide when a category has multiple cards."""
        results_df = pd.DataFrame(
            {
                "Card": ["Card A", "Card B"],
                "Category": ["Dining", "Dining"],
                "Amount": [100.0, 200.0],
            }
        )
        card_a = CreditCard(
            name="Card A",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.02,
            categories={categories["dining"]: CardCategory(rate=0.05)},
        )
        card_b = CreditCard(
            name="Card B",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.02,
            categories={categories["dining"]: CardCategory(rate=0.03)},
        )
        result = generate_priority_guide(
            results_df, [card_a, card_b], "", TRANSLATIONS["en"]
        )
        assert "Dining" in result or "مطاعم" in result
        assert "Card A" in result
        assert "Card B" in result

    def test_generate_priority_guide_arabic(self):
        """Test generate_priority_guide with Arabic translations."""
        results_df = pd.DataFrame(
            {
                "Card": ["Card A", "Card B"],
                "Category": ["Dining", "Dining"],
                "Amount": [100.0, 200.0],
            }
        )
        card_a = CreditCard(
            name="Card A",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.02,
            categories={categories["dining"]: CardCategory(rate=0.05)},
        )
        card_b = CreditCard(
            name="Card B",
            reference_link="http://test.com",
            annual_fee=0,
            base_rate=0.02,
            categories={categories["dining"]: CardCategory(rate=0.03)},
        )
        result = generate_priority_guide(
            results_df, [card_a, card_b], "", TRANSLATIONS["ar"]
        )
        assert result


class TestTranslations:
    """Tests for translations integrity."""

    def test_translations_has_en_and_ar(self):
        """Test that translations has both English and Arabic."""
        assert "en" in TRANSLATIONS
        assert "ar" in TRANSLATIONS

    def test_translations_have_same_keys(self):
        """Test that English and Arabic translations have the same keys."""
        en_keys = set(TRANSLATIONS["en"].keys())
        ar_keys = set(TRANSLATIONS["ar"].keys())
        assert en_keys == ar_keys

    def test_translations_have_required_keys(self):
        """Test that translations have required keys."""
        required_keys = [
            "title",
            "description",
            "sidebar_header",
            "optimize_button",
            "currency_symbol",
        ]
        for key in required_keys:
            assert key in TRANSLATIONS["en"]
            assert key in TRANSLATIONS["ar"]

    def test_translations_values_are_non_empty(self):
        """Test that all translation values are non-empty strings."""
        for lang in ["en", "ar"]:
            for key, value in TRANSLATIONS[lang].items():
                assert isinstance(value, str)
                assert len(value) > 0

    def test_category_translations_exist(self):
        """Test that all category translations exist."""
        category_keys = [
            "Dining",
            "Grocery",
            "Gas Station",
            "Pharmacy",
            "Travel & Hotels",
            "Education",
            "Medical Care",
            "Online Shopping (Local)",
            "International Spend",
            "Other Local Spend",
        ]
        for key in category_keys:
            assert key in TRANSLATIONS["en"]
            assert key in TRANSLATIONS["ar"]
