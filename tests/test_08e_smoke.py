import os
import unittest
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch

from api.index import _status_payload, handler
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


def _minute_chart_response():
    return FakeResponse({
        "return_code": 0,
        "stk_min_pole_chart_qry": [{
            "cntr_tm": "20260930101500",
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
    def test_minute_chart_uses_ka10080_and_normalizes_mock_rows(self, post):
        post.return_value = _minute_chart_response()
        api = KiwoomAPI(
            app_key="minute-test-app-key",
            app_secret="minute-test-app-secret",
            base_url="https://mockapi.kiwoom.com",
            paper=True,
        )
        api._throttle = lambda: None

        result = api.get_minute_chart("005930", tick=1)

        self.assertEqual(result[0]["datetime"], "20260930101500")
        self.assertEqual(result[0]["close"], 105.0)
        self.assertEqual(result[0]["volume"], 1000.0)
        request = post.call_args
        self.assertEqual(request.args[0], "https://mockapi.kiwoom.com/api/dostk/chart")
        self.assertEqual(request.kwargs["headers"]["api-id"], "ka10080")
        self.assertEqual(request.kwargs["json"], {
            "stk_cd": "005930",
            "tic_scope": "1",
            "upd_stkpc_tp": "1",
        })

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

    def test_vercel_entrypoint_is_paper_only_and_readonly(self):
        with patch.dict(
            os.environ,
            {
                "KIWOOM_APP_KEY": "vercel-test-app-key",
                "KIWOOM_APP_SECRET": "vercel-test-app-secret",
            },
            clear=False,
        ), patch("api.index.KiwoomAPI") as api_class:
            response = _status_payload()

        api_class.assert_called_once_with(
            app_key="vercel-test-app-key",
            app_secret="vercel-test-app-secret",
            paper=True,
        )
        self.assertEqual(
            response,
            {"ok": True, "mode": "paper", "readonly": True},
        )

    def test_vercel_handler_uses_supported_python_runtime_contract(self):
        self.assertTrue(issubclass(handler, BaseHTTPRequestHandler))

    def test_explicit_credentials_do_not_enable_live_mode(self):
        api = KiwoomAPI(
            app_key="explicit-test-app-key",
            app_secret="explicit-test-app-secret",
            paper=True,
        )

        self.assertTrue(api.is_paper)
        self.assertEqual(api.auth.app_key, "explicit-test-app-key")
        self.assertEqual(api.auth.app_secret, "explicit-test-app-secret")


if __name__ == "__main__":
    unittest.main()
