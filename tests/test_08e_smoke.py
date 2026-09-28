import os
import unittest
from unittest.mock import patch

from api.kiwoom_api import KiwoomAPI
from order import LiveOrderDisabledError


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _chart_response():
    return FakeResponse({
        "return_code": 0,
        "stk_dt_pole_chart_qry": [{
            "dt": "20260925",
            "open_pric": "100",
            "high_pric": "110",
            "low_pric": "90",
            "cur_prc": "105",
            "trde_qty": "1000",
        }],
    })


def _run_readonly_smoke():
    with patch.dict(
        os.environ,
        {
            "KIWOOM_APP_KEY": "step08e-test-app-key",
            "KIWOOM_APP_SECRET": "step08e-test-app-secret",
            "KIWOOM_BASE_URL": "https://mockapi.kiwoom.com",
        },
        clear=False,
    ), patch(
        "api.kiwoom_api.KiwoomAuth.headers",
        return_value={"authorization": "Bearer test-token"},
    ), patch(
        "api.kiwoom_api.requests.post",
        return_value=_chart_response(),
    ) as post:
        api = KiwoomAPI(paper=True)
        api._throttle = lambda: None

        assert api.is_paper is True
        assert api.auth.app_key == os.environ["KIWOOM_APP_KEY"]
        assert api.auth.app_secret == os.environ["KIWOOM_APP_SECRET"]

        first = api.get_daily_chart("005930", base_dt="20260925", limit=1)
        second = api.get_daily_chart("005930", base_dt="20260925", limit=1)

        assert first == second
        assert post.call_count == 1


def test_08e_readonly_smoke():
    """Read-only chart access remains paper-only and cache-backed."""
    _run_readonly_smoke()


class Step08ESmokeTests(unittest.TestCase):
    def test_08e_readonly_smoke(self):
        _run_readonly_smoke()

    @patch("api.kiwoom_api.requests.post")
    def test_live_orders_fail_closed_without_network(self, post):
        with patch.dict(
            os.environ,
            {
                "KIWOOM_APP_KEY": "step08e-test-app-key",
                "KIWOOM_APP_SECRET": "step08e-test-app-secret",
            },
            clear=False,
        ):
            api = KiwoomAPI(paper=False)

            with self.assertRaises(LiveOrderDisabledError):
                api.buy_market("005930", 1)
            with self.assertRaises(LiveOrderDisabledError):
                api.sell_market("005930", 1)

        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
