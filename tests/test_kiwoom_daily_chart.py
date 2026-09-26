import unittest
from unittest.mock import patch

from api.kiwoom_api import KiwoomAPI


class FakeAuth:
    base_url = "https://api.kiwoom.com"

    def headers(self):
        return {"authorization": "Bearer test-token"}


class FakeResponse:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class KiwoomDailyChartTests(unittest.TestCase):
    def make_api(self):
        api = KiwoomAPI(FakeAuth(), paper=True)
        api._throttle = lambda: None
        return api

    @patch("api.kiwoom_api.requests.post")
    def test_requests_adjusted_daily_bars_using_kiwoom_chart_contract(self, post):
        post.return_value = FakeResponse({
            "return_code": 0,
            "stk_dt_pole_chart_qry": [{
                "dt": "20260925", "open_pric": "100", "high_pric": "110",
                "low_pric": "90", "cur_prc": "105", "trde_qty": "1234",
            }],
        })

        result = self.make_api().get_daily_chart("005930", base_dt="20260925")

        self.assertEqual(result, [{
            "date": "20260925", "open": 100, "high": 110,
            "low": 90, "close": 105, "volume": 1234,
        }])
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.kiwoom.com/api/dostk/chart")
        self.assertEqual(kwargs["headers"]["api-id"], "ka10081")
        self.assertEqual(kwargs["json"], {
            "stk_cd": "005930", "base_dt": "20260925", "upd_stkpc_tp": "1",
        })
        self.assertEqual(kwargs["timeout"], 10)

    @patch("api.kiwoom_api.requests.post")
    def test_follows_continuation_and_returns_unique_bars_oldest_first(self, post):
        post.side_effect = [
            FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [
                {"dt": "20260925", "open_pric": "2", "high_pric": "2", "low_pric": "2", "cur_prc": "2", "trde_qty": "20"},
                {"dt": "20260924", "open_pric": "1", "high_pric": "1", "low_pric": "1", "cur_prc": "1", "trde_qty": "10"},
            ]}, {"cont-yn": "Y", "next-key": "next-1"}),
            FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [
                {"dt": "20260924", "open_pric": "1", "high_pric": "1", "low_pric": "1", "cur_prc": "1", "trde_qty": "10"},
                {"dt": "20260923", "open_pric": "3", "high_pric": "3", "low_pric": "3", "cur_prc": "3", "trde_qty": "30"},
            ]}),
        ]

        result = self.make_api().get_daily_chart("005930", base_dt="20260925")

        self.assertEqual([bar["date"] for bar in result], ["20260923", "20260924", "20260925"])
        self.assertEqual(len(result), 3)
        second_headers = post.call_args_list[1].kwargs["headers"]
        self.assertEqual(second_headers["cont-yn"], "Y")
        self.assertEqual(second_headers["next-key"], "next-1")

    @patch("api.kiwoom_api.requests.post")
    def test_raises_on_api_error_instead_of_returning_empty_success(self, post):
        post.return_value = FakeResponse({"return_code": 1, "return_msg": "invalid code"})

        with self.assertRaisesRegex(RuntimeError, "invalid code"):
            self.make_api().get_daily_chart("NOT-A-CODE", base_dt="20260925")


    @patch("api.kiwoom_api.requests.post")
    def test_rejects_malformed_ohlcv_rows(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [{
            "dt": "20260925", "open_pric": "0", "high_pric": "110",
            "low_pric": "90", "cur_prc": "105", "trde_qty": "1234",
        }]})

        with self.assertRaisesRegex(RuntimeError, "Invalid Kiwoom daily chart row"):
            self.make_api().get_daily_chart("005930")

    @patch("api.kiwoom_api.requests.post")
    def test_limits_results_to_latest_requested_number_of_days(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [
            {"dt": "20260925", "open_pric": "3", "high_pric": "3", "low_pric": "3", "cur_prc": "3", "trde_qty": "30"},
            {"dt": "20260924", "open_pric": "2", "high_pric": "2", "low_pric": "2", "cur_prc": "2", "trde_qty": "20"},
            {"dt": "20260923", "open_pric": "1", "high_pric": "1", "low_pric": "1", "cur_prc": "1", "trde_qty": "10"},
        ]})

        result = self.make_api().get_daily_chart("005930", limit=2)

        self.assertEqual([bar["date"] for bar in result], ["20260924", "20260925"])

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_boolean_limit(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": []})
        with self.assertRaisesRegex(ValueError, "limit"):
            self.make_api().get_daily_chart("005930", limit=True)

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_boolean_page_limit(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": []})
        with self.assertRaisesRegex(ValueError, "max_pages"):
            self.make_api().get_daily_chart("005930", max_pages=True)

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_non_mapping_chart_rows(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [None]})

        with self.assertRaisesRegex(RuntimeError, "Invalid Kiwoom daily chart row"):
            self.make_api().get_daily_chart("005930")

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_oversized_chart_page(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [
            {"dt": "20260925", "open_pric": "1", "high_pric": "1", "low_pric": "1", "cur_prc": "1", "trde_qty": "1"}
        ] * 10001})

        with self.assertRaisesRegex(RuntimeError, "too many rows"):
            self.make_api().get_daily_chart("005930")

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_negative_daily_price(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [{
            "dt": "20260925", "open_pric": "-100", "high_pric": "110",
            "low_pric": "90", "cur_prc": "105", "trde_qty": "1234",
        }]})

        with self.assertRaisesRegex(RuntimeError, "Invalid Kiwoom daily chart row"):
            self.make_api().get_daily_chart("005930")

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_missing_daily_rows_field(self, post):
        post.return_value = FakeResponse({"return_code": 0})

        with self.assertRaisesRegex(RuntimeError, "rows field"):
            self.make_api().get_daily_chart("005930")

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_null_daily_rows_field(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": None})

        with self.assertRaisesRegex(RuntimeError, "rows field"):
            self.make_api().get_daily_chart("005930")

    @patch("api.kiwoom_api.requests.post")
    def test_rejects_invalid_calendar_date_in_response_row(self, post):
        post.return_value = FakeResponse({"return_code": 0, "stk_dt_pole_chart_qry": [{
            "dt": "20260231", "open_pric": "100", "high_pric": "110",
            "low_pric": "90", "cur_prc": "105", "trde_qty": "1000",
        }]})

        with self.assertRaisesRegex(RuntimeError, "Invalid Kiwoom daily chart row"):
            self.make_api().get_daily_chart("005930")

    def test_rejects_invalid_base_date_before_network_call(self):
        with self.assertRaisesRegex(ValueError, "base_dt"):
            self.make_api().get_daily_chart("005930", base_dt="20261399")


if __name__ == "__main__":
    unittest.main()
