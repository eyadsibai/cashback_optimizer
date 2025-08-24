from typing import Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from cards.alrajhi import get_alrajhi_card
from cards.bsf import get_lifestyle_card
from cards.nayfat import get_nayfat_card
from cards.nbd import get_nbd_card
from cards.sabb import get_sabb_card
from cards.saib import get_saib_card
from cards.snb import get_snb_card
from models import CreditCard, categories
from optimizer import solve_optimization

app = FastAPI()


class Spending(BaseModel):
    monthly_spending: Dict[str, float]
    selected_card_names: List[str]


@app.get("/cards")
def get_cards() -> List[Dict]:
    """Returns a list of all available credit cards."""
    all_cards = [
        get_snb_card(),
        get_alrajhi_card(),
        get_nbd_card(),
        get_lifestyle_card(),
        get_saib_card(),
        get_sabb_card(),
        get_nayfat_card(),
    ]
    return [card.__dict__ for card in all_cards]


@app.get("/categories")
def get_categories() -> List[Dict]:
    """Returns a list of all spending categories."""
    return [cat.__dict__ for cat in categories.values()]


@app.post("/optimize")
def optimize(spending: Spending):
    """
    Runs the optimization logic based on user's spending and selected cards.
    """
    all_cards = [
        get_snb_card(),
        get_alrajhi_card(),
        get_nbd_card(),
        get_lifestyle_card(),
        get_saib_card(),
        get_sabb_card(),
        get_nayfat_card(),
    ]
    selected_cards = [
        card
        for card in all_cards
        if card.name in spending.selected_card_names
    ]
    optimization_result = solve_optimization(
        selected_cards, spending.monthly_spending
    )

    if optimization_result is None:
        return {"error": "No solution found"}

    # Convert DataFrame to a list of dicts for JSON serialization
    results_list = optimization_result.results_df.to_dict(orient="records")

    return {
        "results_df": results_list,
        "total_savings": optimization_result.total_savings,
        "chosen_plan": optimization_result.chosen_plan,
    }
