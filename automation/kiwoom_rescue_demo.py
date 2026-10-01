"""Offline rescue-strategy demonstration using synthetic portfolio data only.

This script never reads credentials, account state, broker clients, or network
resources. It exists as a deterministic regression fixture for the paper-only
rescue allocation rules.
"""

import pandas as pd

from api.demo_portfolio import split_quantity_evenly
from api.sample_portfolio import SAMPLE_CASH, SAMPLE_POSITIONS


# Exposed for the offline regression tests.
history = {
    code: pd.DataFrame({"close": [position["avg"], position["current"]]})
    for code, position in SAMPLE_POSITIONS.items()
}

# Keep this fixture's ranking explicit: it is not a live recommendation.
picks = pd.DataFrame(
    {
        "code": ["DEMO-001", "DEMO-003"],
        "score": [0.6707, -0.4907],
    }
)


def main():
    print(f"가상 샘플 현금: {SAMPLE_CASH:,}원")
    for code, position in SAMPLE_POSITIONS.items():
        loss_rate = (position["current"] / position["avg"]) - 1
        if loss_rate <= -0.30:
            for quantity in split_quantity_evenly(position["qty"], 3):
                if quantity:
                    print(f"{position['name']} ({code}) {quantity}주 가상 매도")


if __name__ == "__main__":
    main()
