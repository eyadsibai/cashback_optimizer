"""Tests for card configuration modules."""

import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from models import CreditCard, LifestyleCard, categories
from cards.snb import get_snb_card
from cards.alrajhi import get_alrajhi_card
from cards.nbd import get_nbd_card
from cards.bsf import get_lifestyle_card, generate_plans, generate_life_style_plans
from cards.sabb import get_sabb_card
from cards.saib import get_saib_card
from cards.nayfat import get_nayfat_card


class TestSNBCard:
    """Tests for SNB card configuration."""

    def test_get_snb_card_returns_credit_card(self):
        """Test that get_snb_card returns a CreditCard instance."""
        card = get_snb_card()
        assert isinstance(card, CreditCard)

    def test_snb_card_has_name(self):
        """Test that SNB card has a name."""
        card = get_snb_card()
        assert card.name == "SNB Premium Cashback"

    def test_snb_card_has_reference_link(self):
        """Test that SNB card has a reference link."""
        card = get_snb_card()
        assert card.reference_link
        assert card.reference_link.startswith("http")

    def test_snb_card_has_annual_fee(self):
        """Test that SNB card has an annual fee."""
        card = get_snb_card()
        assert card.annual_fee >= 0

    def test_snb_card_has_base_rate(self):
        """Test that SNB card has a base rate."""
        card = get_snb_card()
        assert card.base_rate >= 0

    def test_snb_card_has_categories(self):
        """Test that SNB card has categories configured."""
        card = get_snb_card()
        assert len(card.categories) > 0


class TestAlrajhiCard:
    """Tests for Alrajhi card configuration."""

    def test_get_alrajhi_card_returns_credit_card(self):
        """Test that get_alrajhi_card returns a CreditCard instance."""
        card = get_alrajhi_card()
        assert isinstance(card, CreditCard)

    def test_alrajhi_card_has_name(self):
        """Test that Alrajhi card has a name."""
        card = get_alrajhi_card()
        assert card.name

    def test_alrajhi_card_has_reference_link(self):
        """Test that Alrajhi card has a reference link."""
        card = get_alrajhi_card()
        assert card.reference_link

    def test_alrajhi_card_has_annual_fee(self):
        """Test that Alrajhi card has an annual fee."""
        card = get_alrajhi_card()
        assert card.annual_fee >= 0


class TestNBDCard:
    """Tests for NBD card configuration."""

    def test_get_nbd_card_returns_credit_card(self):
        """Test that get_nbd_card returns a CreditCard instance."""
        card = get_nbd_card()
        assert isinstance(card, CreditCard)

    def test_nbd_card_has_name(self):
        """Test that NBD card has a name."""
        card = get_nbd_card()
        assert card.name

    def test_nbd_card_has_reference_link(self):
        """Test that NBD card has a reference link."""
        card = get_nbd_card()
        assert card.reference_link

    def test_nbd_card_has_annual_fee(self):
        """Test that NBD card has an annual fee."""
        card = get_nbd_card()
        assert card.annual_fee >= 0


class TestSABBCard:
    """Tests for SABB card configuration."""

    def test_get_sabb_card_returns_credit_card(self):
        """Test that get_sabb_card returns a CreditCard instance."""
        card = get_sabb_card()
        assert isinstance(card, CreditCard)

    def test_sabb_card_has_name(self):
        """Test that SABB card has a name."""
        card = get_sabb_card()
        assert card.name

    def test_sabb_card_has_reference_link(self):
        """Test that SABB card has a reference link."""
        card = get_sabb_card()
        assert card.reference_link

    def test_sabb_card_has_annual_fee(self):
        """Test that SABB card has an annual fee."""
        card = get_sabb_card()
        assert card.annual_fee >= 0


class TestSAIBCard:
    """Tests for SAIB card configuration."""

    def test_get_saib_card_returns_credit_card(self):
        """Test that get_saib_card returns a CreditCard instance."""
        card = get_saib_card()
        assert isinstance(card, CreditCard)

    def test_saib_card_has_name(self):
        """Test that SAIB card has a name."""
        card = get_saib_card()
        assert card.name

    def test_saib_card_has_reference_link(self):
        """Test that SAIB card has a reference link."""
        card = get_saib_card()
        assert card.reference_link

    def test_saib_card_has_annual_fee(self):
        """Test that SAIB card has an annual fee."""
        card = get_saib_card()
        assert card.annual_fee >= 0


class TestNayfatCard:
    """Tests for Nayfat card configuration."""

    def test_get_nayfat_card_returns_credit_card(self):
        """Test that get_nayfat_card returns a CreditCard instance."""
        card = get_nayfat_card()
        assert isinstance(card, CreditCard)

    def test_nayfat_card_has_name(self):
        """Test that Nayfat card has a name."""
        card = get_nayfat_card()
        assert card.name

    def test_nayfat_card_has_reference_link(self):
        """Test that Nayfat card has a reference link."""
        card = get_nayfat_card()
        assert card.reference_link

    def test_nayfat_card_has_annual_fee(self):
        """Test that Nayfat card has an annual fee."""
        card = get_nayfat_card()
        assert card.annual_fee >= 0


class TestBSFLifestyleCard:
    """Tests for BSF Lifestyle card configuration."""

    def test_get_lifestyle_card_returns_lifestyle_card(self):
        """Test that get_lifestyle_card returns a LifestyleCard instance."""
        card = get_lifestyle_card()
        assert isinstance(card, LifestyleCard)

    def test_lifestyle_card_has_name(self):
        """Test that Lifestyle card has a name."""
        card = get_lifestyle_card()
        assert card.name == "BSF Lifestyle"

    def test_lifestyle_card_has_reference_link(self):
        """Test that Lifestyle card has a reference link."""
        card = get_lifestyle_card()
        assert card.reference_link
        assert card.reference_link.startswith("http")

    def test_lifestyle_card_has_plans(self):
        """Test that Lifestyle card has plans."""
        card = get_lifestyle_card()
        assert len(card.plans) > 0

    def test_lifestyle_card_has_base_rate(self):
        """Test that Lifestyle card has a base rate."""
        card = get_lifestyle_card()
        assert card.base_rate >= 0

    def test_lifestyle_card_has_fee_waiver_configuration(self):
        """Test that Lifestyle card has fee waiver configuration."""
        card = get_lifestyle_card()
        assert card.annual_fee_if_condition_not_met is not None
        assert card.minimum_annual_spend_for_fee_waiver is not None


class TestGeneratePlans:
    """Tests for the generate_plans function."""

    def test_generate_plans_with_valid_categories(self):
        """Test generate_plans with valid categories."""
        test_categories = [
            categories["dining"],
            categories["grocery"],
            categories["travel_hotels"],
            categories["medical_care"],
            categories["education"],
        ]
        plans = generate_plans(test_categories)
        assert len(plans) > 0

    def test_generate_plans_each_plan_has_required_keys(self):
        """Test that each plan has main, major, and minor keys."""
        test_categories = [
            categories["dining"],
            categories["grocery"],
            categories["travel_hotels"],
            categories["medical_care"],
            categories["education"],
        ]
        plans = generate_plans(test_categories)
        for plan in plans:
            assert "main" in plan
            assert "major" in plan
            assert "minor" in plan

    def test_generate_plans_correct_distribution(self):
        """Test that plans have correct distribution of categories."""
        test_categories = [
            categories["dining"],
            categories["grocery"],
            categories["travel_hotels"],
            categories["medical_care"],
            categories["education"],
        ]
        plans = generate_plans(test_categories)
        for plan in plans:
            assert len(plan["major"]) == 2
            assert len(plan["minor"]) == 2

    def test_generate_plans_with_insufficient_categories(self):
        """Test generate_plans with fewer than 5 categories."""
        test_categories = [categories["dining"], categories["grocery"]]
        plans = generate_plans(test_categories)
        assert len(plans) == 0

    def test_generate_plans_uniqueness(self):
        """Test that each category in a plan is unique."""
        test_categories = [
            categories["dining"],
            categories["grocery"],
            categories["travel_hotels"],
            categories["medical_care"],
            categories["education"],
        ]
        plans = generate_plans(test_categories)
        for plan in plans:
            all_cats = [plan["main"]] + plan["major"] + plan["minor"]
            assert len(all_cats) == len(set(all_cats))


class TestGenerateLifeStylePlans:
    """Tests for the generate_life_style_plans function."""

    def test_generate_life_style_plans_returns_list(self):
        """Test that generate_life_style_plans returns a list."""
        plans = generate_life_style_plans()
        assert isinstance(plans, list)

    def test_generate_life_style_plans_contains_lifestyle_plans(self):
        """Test that all items are LifestylePlan instances."""
        from models import LifestylePlan

        plans = generate_life_style_plans()
        assert len(plans) > 0
        for plan in plans:
            assert isinstance(plan, LifestylePlan)

    def test_generate_life_style_plans_have_names(self):
        """Test that all plans have names."""
        plans = generate_life_style_plans()
        for plan in plans:
            assert plan.name
            assert "10%" in plan.name
            assert "3%" in plan.name
            assert "2%" in plan.name

    def test_generate_life_style_plans_have_categories(self):
        """Test that all plans have categories configured."""
        plans = generate_life_style_plans()
        for plan in plans:
            assert len(plan.categories_rate_cap) > 0
