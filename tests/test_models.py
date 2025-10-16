"""Tests for models.py data structures."""

import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from models import (
    CardCategory,
    CashbackTier,
    Category,
    CreditCard,
    LifestyleCard,
    LifestylePlan,
    OptimizationResult,
    TierCategory,
    categories,
)
import pandas as pd


class TestCategory:
    """Tests for Category dataclass."""

    def test_category_creation(self):
        """Test creating a Category."""
        cat = Category(key="Test", display_name="Test Category")
        assert cat.key == "Test"
        assert cat.display_name == "Test Category"
        assert cat.parent_key is None

    def test_category_with_parent(self):
        """Test creating a Category with parent."""
        cat = Category(key="Test", display_name="Test Category", parent_key="Parent")
        assert cat.parent_key == "Parent"

    def test_category_is_frozen(self):
        """Test that Category is immutable."""
        cat = Category(key="Test", display_name="Test")
        with pytest.raises(Exception):  # FrozenInstanceError
            cat.key = "NewKey"


class TestCardCategory:
    """Tests for CardCategory dataclass."""

    def test_card_category_creation(self):
        """Test creating a CardCategory."""
        card_cat = CardCategory(rate=0.05)
        assert card_cat.rate == 0.05
        assert card_cat.cap == float("inf")

    def test_card_category_with_cap(self):
        """Test creating a CardCategory with cap."""
        card_cat = CardCategory(rate=0.05, cap=100)
        assert card_cat.rate == 0.05
        assert card_cat.cap == 100


class TestTierCategory:
    """Tests for TierCategory dataclass."""

    def test_tier_category_creation(self):
        """Test creating a TierCategory."""
        tier_cat = TierCategory(rate=0.05)
        assert tier_cat.rate == 0.05
        assert tier_cat.cap == float("inf")

    def test_tier_category_with_cap(self):
        """Test creating a TierCategory with cap."""
        tier_cat = TierCategory(rate=0.05, cap=100)
        assert tier_cat.rate == 0.05
        assert tier_cat.cap == 100


class TestCashbackTier:
    """Tests for CashbackTier dataclass."""

    def test_cashback_tier_creation(self):
        """Test creating a CashbackTier."""
        tier = CashbackTier(
            name="Tier 1",
            min_spend=0,
            max_spend=1000,
            categories={categories["dining"]: TierCategory(rate=0.05)},
            base_rate=0.01,
        )
        assert tier.name == "Tier 1"
        assert tier.min_spend == 0
        assert tier.max_spend == 1000
        assert tier.base_rate == 0.01
        assert categories["dining"] in tier.categories


class TestCreditCard:
    """Tests for CreditCard dataclass."""

    def test_credit_card_minimal(self):
        """Test creating a minimal CreditCard."""
        card = CreditCard(name="Test Card", reference_link="http://test.com", annual_fee=100)
        assert card.name == "Test Card"
        assert card.reference_link == "http://test.com"
        assert card.annual_fee == 100
        assert card.monthly_cap == float("inf")
        assert card.annual_cap == float("inf")
        assert card.min_spend_for_cashback == 0.0
        assert card.minimum_annual_spend_for_fee_waiver is None
        assert card.annual_fee_if_condition_not_met is None
        assert len(card.grouped_monthly_caps) == 0
        assert len(card.categories) == 0
        assert card.base_rate == 0.0
        assert len(card.tiers) == 0

    def test_credit_card_with_categories(self):
        """Test creating a CreditCard with categories."""
        card = CreditCard(
            name="Test Card",
            reference_link="http://test.com",
            annual_fee=100,
            categories={categories["dining"]: CardCategory(rate=0.05, cap=100)},
            base_rate=0.01,
        )
        assert card.base_rate == 0.01
        assert categories["dining"] in card.categories
        assert card.categories[categories["dining"]].rate == 0.05

    def test_credit_card_with_caps(self):
        """Test creating a CreditCard with caps."""
        card = CreditCard(
            name="Test Card",
            reference_link="http://test.com",
            annual_fee=100,
            monthly_cap=500,
            annual_cap=6000,
        )
        assert card.monthly_cap == 500
        assert card.annual_cap == 6000

    def test_credit_card_with_min_spend(self):
        """Test creating a CreditCard with minimum spend requirement."""
        card = CreditCard(
            name="Test Card",
            reference_link="http://test.com",
            annual_fee=100,
            min_spend_for_cashback=500,
        )
        assert card.min_spend_for_cashback == 500

    def test_credit_card_with_fee_waiver(self):
        """Test creating a CreditCard with fee waiver condition."""
        card = CreditCard(
            name="Test Card",
            reference_link="http://test.com",
            annual_fee=0,
            annual_fee_if_condition_not_met=100,
            minimum_annual_spend_for_fee_waiver=10000,
        )
        assert card.annual_fee == 0
        assert card.annual_fee_if_condition_not_met == 100
        assert card.minimum_annual_spend_for_fee_waiver == 10000

    def test_credit_card_with_tiers(self):
        """Test creating a CreditCard with tiers."""
        tier = CashbackTier(
            name="Tier 1",
            min_spend=0,
            max_spend=1000,
            categories={categories["dining"]: TierCategory(rate=0.05)},
            base_rate=0.01,
        )
        card = CreditCard(
            name="Test Card",
            reference_link="http://test.com",
            annual_fee=100,
            tiers=[tier],
        )
        assert len(card.tiers) == 1
        assert card.tiers[0].name == "Tier 1"


class TestLifestylePlan:
    """Tests for LifestylePlan dataclass."""

    def test_lifestyle_plan_creation(self):
        """Test creating a LifestylePlan."""
        plan = LifestylePlan(
            name="Plan 1",
            categories_rate_cap=[{categories["dining"]: CardCategory(rate=0.10, cap=250)}],
        )
        assert plan.name == "Plan 1"
        assert len(plan.categories_rate_cap) == 1


class TestLifestyleCard:
    """Tests for LifestyleCard dataclass."""

    def test_lifestyle_card_creation(self):
        """Test creating a LifestyleCard."""
        plan = LifestylePlan(
            name="Plan 1",
            categories_rate_cap=[{categories["dining"]: CardCategory(rate=0.10, cap=250)}],
        )
        card = LifestyleCard(
            name="Lifestyle Card",
            reference_link="http://test.com",
            annual_fee=100,
            plans=[plan],
        )
        assert card.name == "Lifestyle Card"
        assert len(card.plans) == 1
        assert card.plans[0].name == "Plan 1"
        assert isinstance(card, CreditCard)  # LifestyleCard inherits from CreditCard


class TestOptimizationResult:
    """Tests for OptimizationResult dataclass."""

    def test_optimization_result_creation(self):
        """Test creating an OptimizationResult."""
        df = pd.DataFrame(
            {
                "Card": ["Card A", "Card B"],
                "Category": ["Dining", "Grocery"],
                "Amount": [100, 200],
            }
        )
        result = OptimizationResult(results_df=df, total_savings=300, chosen_plan="Plan 1")
        assert result.total_savings == 300
        assert result.chosen_plan == "Plan 1"
        assert len(result.results_df) == 2

    def test_optimization_result_empty_df(self):
        """Test creating an OptimizationResult with empty DataFrame."""
        result = OptimizationResult(results_df=pd.DataFrame(), total_savings=0, chosen_plan="")
        assert result.total_savings == 0
        assert result.chosen_plan == ""
        assert result.results_df.empty


class TestCategoriesConstant:
    """Tests for the categories constant."""

    def test_categories_exists(self):
        """Test that categories constant is defined."""
        assert categories is not None
        assert isinstance(categories, dict)

    def test_categories_has_expected_keys(self):
        """Test that categories has expected keys."""
        expected_keys = [
            "dining",
            "grocery",
            "gas_station",
            "pharmacy",
            "travel_hotels",
            "education",
            "medical_care",
            "online_shopping_local",
            "international_spend",
            "other_local_spend",
        ]
        for key in expected_keys:
            assert key in categories

    def test_categories_values_are_category_instances(self):
        """Test that all values in categories are Category instances."""
        for cat in categories.values():
            assert isinstance(cat, Category)

    def test_categories_have_display_names(self):
        """Test that all categories have display names."""
        for cat in categories.values():
            assert cat.display_name
            assert cat.key
