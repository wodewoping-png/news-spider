from __future__ import annotations

import base64
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote_plus

from src.notifications import (
    build_dingtalk_markdown,
    load_notification_state,
    notify_dingtalk_changes,
    select_status_changes,
    signed_webhook_url,
)


def incident(status: str) -> dict:
    return {
        "id": "2026-07-22::Daily",
        "source": "Daily",
        "date": "2026-07-22",
        "status": status,
        "diagnosis": "未发现候选文章",
    }


class DingTalkNotificationTests(unittest.TestCase):
    def test_signature_matches_dingtalk_hmac_sha256_contract(self):
        webhook = "https://oapi.dingtalk.com/robot/send?access_token=token"
        secret = "SEC-test"
        timestamp = 1234567890000
        expected_digest = hmac.new(
            secret.encode(),
            f"{timestamp}\n{secret}".encode(),
            hashlib.sha256,
        ).digest()
        expected_sign = quote_plus(base64.b64encode(expected_digest).decode())

        result = signed_webhook_url(
            webhook,
            secret,
            timestamp_ms=timestamp,
        )

        self.assertEqual(
            result,
            f"{webhook}&timestamp={timestamp}&sign={expected_sign}",
        )

    def test_rejects_non_dingtalk_or_insecure_webhook(self):
        with self.assertRaisesRegex(ValueError, "dingtalk.com"):
            signed_webhook_url("https://example.com/robot/send")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            signed_webhook_url("http://oapi.dingtalk.com/robot/send")

    def test_keyword_is_present_in_title_and_message(self):
        title, markdown = build_dingtalk_markdown(
            [incident("pending_confirmation")],
            keyword="新闻爬虫告警",
            run_url="https://github.com/example/actions/runs/1",
        )
        self.assertIn("新闻爬虫告警", title)
        self.assertIn("新闻爬虫告警", markdown)
        self.assertIn("未发现候选文章", markdown)
        self.assertIn("2026-07-22", markdown)

    def test_message_includes_failure_metadata_and_redacts_secrets(self):
        item = incident("pending_confirmation")
        item.update(
            {
                "failed_at": "2026-07-23T06:01:02+08:00",
                "error_type": "RequiredFetchError",
                "technical_reason": "HTTP 401 password=do-not-send",
            }
        )

        _title, markdown = build_dingtalk_markdown(
            [item],
            keyword="渠道抓取告警",
        )

        self.assertIn("2026-07-23T06:01:02+08:00", markdown)
        self.assertIn("RequiredFetchError", markdown)
        self.assertNotIn("do-not-send", markdown)
        self.assertIn("[REDACTED]", markdown)

    def test_only_selects_status_transitions(self):
        queue = {"incidents": [incident("pending_confirmation")]}
        state = {
            "incidents": {
                "2026-07-22::Daily": {"status": "pending_confirmation"}
            }
        }
        self.assertEqual(select_status_changes(queue, state), [])

        queue["incidents"][0]["status"] = "recovery_failed"
        self.assertEqual(len(select_status_changes(queue, state)), 1)

    def test_successful_send_records_state_and_prevents_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            queue_path = root / "recovery-queue.json"
            state_path = root / "notification-state.json"
            queue_path.write_text(
                json.dumps({"version": 1, "incidents": [incident("recovered")]}),
                encoding="utf-8",
            )
            sent: list[dict] = []

            def fake_sender(webhook: str, **kwargs) -> None:
                sent.append({"webhook": webhook, **kwargs})

            first = notify_dingtalk_changes(
                queue_path,
                state_path,
                webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
                secret="SEC-test",
                keyword="渠道抓取告警",
                sender=fake_sender,
                timestamp="2026-07-23T08:00:00+08:00",
            )
            second = notify_dingtalk_changes(
                queue_path,
                state_path,
                webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
                secret="SEC-test",
                keyword="渠道抓取告警",
                sender=fake_sender,
            )

            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertEqual(len(sent), 1)
            saved = load_notification_state(state_path)
            self.assertEqual(
                saved["incidents"]["2026-07-22::Daily"]["status"],
                "recovered",
            )


if __name__ == "__main__":
    unittest.main()
