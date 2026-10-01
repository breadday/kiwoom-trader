"""Deterministic synthetic rescue demo; never accesses broker or account APIs."""

import numpy as np
import pandas as pd

from api.demo_portfolio import split_quantity_evenly
from api.sample_portfolio import SAMPLE_CASH, SAMPLE_POSITIONS


# Public globals are intentional: privacy tests inspect the deterministic demo state.
history = {
    code: pd.DataFrame(
        {
            "close": np.linspace(position["avg"], position["current"], 60),
            "volume": np.full(60, 1_000),
        }
    )
    for code, position in SAMPLE_POSITIONS.items()
}

picks = pd.DataFrame(
    [
        {"code": "DEMO-001", "score": 0.6707},
        {"code": "DEMO-003", "score": -0.4907},
    ]
)


def print_virtual_rescue_sales():
    """Print a three-week virtual sale plan for synthetic loss-making positions."""
    for code, position in SAMPLE_POSITIONS.items():
        loss_fraction = (position["current"] - position["avg"]) / position["avg"]
        if loss_fraction <= -0.30:
            for quantity in split_quantity_evenly(position["qty"], 3):
                print(f"{position['name']} ({code}) {quantity}주 가상 매도")


if __name__ == "__main__":
    print(f"가상 샘플 현금: {SAMPLE_CASH:,}원")
    print_virtual_rescue_sales()
