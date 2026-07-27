from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from src.notifications import NotificationError, send_dingtalk


class DingTalkNotificationSecurityTests(unittest.TestCase):
    def test_http_error_does_not_expose_webhook_token(self):
        webhook = (
            "https://oapi.dingtalk.com/robot/send?"
            "access_token=very-sensitive-token"
        )
        error = HTTPError(webhook, 400, "Bad Request", hdrs=None, fp=None)

        with patch("src.notifications.urlopen", side_effect=error):
            with self.assertRaises(NotificationError) as caught:
                send_dingtalk(
                    webhook,
                    secret="",
                    title="渠道抓取告警",
                    markdown="渠道抓取告警测试",
                )

        self.assertNotIn("very-sensitive-token", str(caught.exception))
        self.assertIn("HTTP 400", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
