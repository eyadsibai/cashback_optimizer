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
    """Represents a single cashback category on a card."""

    rate: float
    cap: float = float("inf")


@dataclass
class CreditCard:
    """Represents a standard credit card."""

    name: str
    reference_link: str
    annual_fee: float
    monthly_cap: float = float("inf")
    annual_cap: float = float("inf")
    grouped_monthly_caps: List[tuple[float, List[Category]]] = field(default_factory=list)
    categories: Dict[Category, CardCategory] = field(default_factory=dict)
    base_rate: float = 0.0



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
    "dining": Category(key="dining", display_name="Dining"),
    "grocery": Category(key="grocery", display_name="Grocery"),
    "gas_station": Category(key="gas_station", display_name="Gas Station"),
    "pharmacy": Category(key="pharmacy", display_name="Pharmacy"),
    "travel_hotels": Category(key="travel_hotels", display_name="Travel & Hotels"),
    "education": Category(key="education", display_name="Education"),
    "medical_care": Category(key="medical_care", display_name="Medical Care"),
    "online_shopping_local": Category(key="online_shopping_local", 
                                      display_name="Online Shopping (Local)"),
    "international_spend_non_eur": Category(key="international_spend_non_eur", 
                                            display_name="International Spend (Non-EUR)"),
    "other_local_spend": Category(key="other_local_spend", display_name="Other Local Spend"),
}
