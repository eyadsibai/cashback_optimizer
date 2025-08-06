"""
This module defines the data models for credit card cashback categories and tiers."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Category:
    """Represents a single category with its internal key and display name."""

    key: str
    display_name: str
    parent_key: str | None = None


@dataclass
class CardCategory:
    """Represents a single cashback category on a card for non-tiered cards."""

    rate: float
    cap: float = float("inf")


@dataclass
class TierCategory:
    """Represents the cashback details for a category within a specific tier."""

    rate: float
    cap: float = float("inf")


@dataclass
class CashbackTier:
    """Represents a cashback tier based on total monthly spend."""

    name: str
    min_spend: float
    max_spend: float
    categories: Dict[Category, TierCategory]
    base_rate: float  # A base rate for categories not explicitly listed in the tier


@dataclass
class CreditCard:
    """Represents a standard credit card."""

    name: str
    reference_link: str
    annual_fee: float
    monthly_cap: float = float("inf")
    annual_cap: float = float("inf")
    min_spend_for_cashback: float = 0.0  # New attribute for minimum spend
    grouped_monthly_caps: List[tuple[float, List[Category]]] = field(
        default_factory=list
    )
    categories: Dict[Category, CardCategory] = field(default_factory=dict)
    base_rate: float = 0.0
    tiers: List[CashbackTier] = field(default_factory=list)


@dataclass
class LifestylePlan:
    """Represents one of the selectable monthly plans for the Lifestyle card."""

    name: str
    categories_rate_cap: List[dict[Category, CardCategory]]


@dataclass
class LifestyleCard(CreditCard):
    """Represents the special Lifestyle card with selectable plans."""

    plans: List[LifestylePlan] = field(default_factory=list)


categories = {
    "dining": Category(key="Dining", display_name="Dining"),
    "grocery": Category(key="Grocery", display_name="Grocery"),
    "gas_station": Category(key="Gas Station", display_name="Gas Station"),
    "pharmacy": Category(key="Pharmacy", display_name="Pharmacy"),
    "travel_hotels": Category(key="Travel & Hotels", display_name="Travel & Hotels"),
    "education": Category(key="Education", display_name="Education"),
    "medical_care": Category(key="Medical Care", display_name="Medical Care"),
    "online_shopping_local": Category(
        key="Online Shopping (Local)", display_name="Online Shopping (Local)"
    ),
    "international_spend_non_eur": Category(
        key="International Spend (Non-EUR)",
        display_name="International Spend (Non-EUR)",
    ),
    "other_local_spend": Category(
        key="Other Local Spend", display_name="Other Local Spend"
    ),
}
