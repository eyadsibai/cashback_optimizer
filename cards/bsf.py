"""
This module provides the configuration for the BSF Bank"""

from itertools import combinations

from models import CardCategory, LifestyleCard, LifestylePlan, categories

lifestyle_base_categories = [
    categories["dining"],
    categories["grocery"],
    categories["travel_hotels"],
    categories["medical_care"],
    categories["education"],
]

def generate_plans(list_of_categories: list) -> list:
    """
    Generates all possible plans from a list of categories.

    Each plan consists of:
    - 1 unique main category
    - 2 unique major categories
    - 2 unique minor categories

    Args:
        categories (list): A list of category names (strings).

    Returns:
        list: A list of dictionaries, where each dictionary represents a unique plan.
              Returns an empty list if there are fewer than 5 categories.
    """
    # A plan requires 1 main + 2 major + 2 minor = 5 unique categories.
    if len(list_of_categories) < 5:
        print("Warning: Need at least 5 categories to form a plan.")
        return []

    all_plans = []

    # 1. Iterate through all possible combinations of 5 categories from the list.
    #    This ensures every group of 5 is considered exactly once.
    for group_of_five in combinations(list_of_categories, 5):
        # 2. Within this group of 5, iterate through each to select it as the main category.
        for main_category in group_of_five:
            # 3. The remaining 4 categories are candidates for major and minor roles.
            remaining_four = list(group_of_five)
            remaining_four.remove(main_category)

            # 4. From the remaining 4, choose 2 to be the major categories.
            for major_categories in combinations(remaining_four, 2):
                # 5. The final 2 categories automatically become the minor ones.
                #    We can find them using set difference for efficiency.
                minor_categories = tuple(set(remaining_four) - set(major_categories))

                # Create the plan dictionary and add it to our list.
                plan = {
                    "main": main_category,
                    "major": list(major_categories),
                    "minor": list(minor_categories),
                }
                all_plans.append(plan)

    return all_plans


def generate_life_style_plans() -> list[LifestylePlan]:
    """
    Generates Lifestyle plans based on predefined categories.

    Returns:
        list[LifestylePlan]: A list of LifestylePlan objects.
    """
    # Generate all possible plans from the base categories
    plans = generate_plans(lifestyle_base_categories)

    lifestyle_plans = []

    for plan in plans:
        main_category = plan["main"]
        major_categories = plan["major"]
        minor_categories = plan["minor"]

        # Create a more descriptive name
        major_cat_names = (
            f"{major_categories[0].display_name}, {major_categories[1].display_name}"
        )
        minor_cat_names = (
            f"{minor_categories[0].display_name}, {minor_categories[1].display_name}"
        )
        plan_name = (
            f"10% on {main_category.display_name}; "
            f"3% on {major_cat_names}; "
            f"2% on {minor_cat_names}"
        )

        lifestyle_plans.append(
            LifestylePlan(
                name=plan_name,
                categories_rate_cap=[
                    {main_category: CardCategory(rate=0.10, cap=250)},
                    {cat: CardCategory(rate=0.03, cap=250) for cat in major_categories},
                    {cat: CardCategory(rate=0.02, cap=250) for cat in minor_categories},
                ],
            )
        )

    return lifestyle_plans


def get_lifestyle_card() -> LifestyleCard:
    """Return BSF Lifestyle credit card configuration."""
    lifestyle_plans = generate_life_style_plans()

    return LifestyleCard(
        name="BSF Lifestyle",
        reference_link=(
            "https://bsf.sa/english/personal/cards/credit/lifestyle-credit-card/"
            "lifestyle"
        ),
        base_rate=0.005,
        annual_fee=0, # the fee if it is waived
        plans=lifestyle_plans,
        annual_fee_if_condition_not_met=287.5,  # Annual fee if not waived
        # The condition to waive the annual fee
        minimum_annual_spend_for_fee_waiver=20000
    )
