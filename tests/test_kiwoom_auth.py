import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from api.kiwoom_auth import KiwoomAuth


class KiwoomAuthLoggingTests(unittest.TestCase):
    @patch("api.kiwoom_auth.requests.post")
    def test_successful_token_exchange_never_logs_the_access_token(self, post):
        token = "sensitive-access-token-value"
        response = post.return_value
        response.json.return_value = {"token": token}
        output = io.StringIO()

        with redirect_stdout(output):
            result = KiwoomAuth("test-app-key", "test-app-secret").get_token()

        self.assertEqual(result, token)
        output_text = output.getvalue()
        self.assertNotIn(token[:8], output_text)
        self.assertNotIn(token[:20], output_text)


if __name__ == "__main__":
    unittest.main()
