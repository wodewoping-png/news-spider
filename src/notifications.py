from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .date_utils import DEFAULT_TIMEZONE
from .recovery import load_queue


STATE_VERSION = 1
NOTIFIABLE_STATUSES = {"pending_confirmation", "recovery_failed", "recovered"}
STATUS_LABELS = {
    "pending_confirmation": "待人工确认",
    "recovery_failed": "补抓失败",
    "recovered": "补抓成功",
}
_SECRET_PATTERN = re.compile(
    r"(?i)((?:access[_-]?token|api[_-]?key|password|secret|authorization)"
    r"(?:%3[dD]|=|:)\s*)[^&\s,;]+"
)


class NotificationError(RuntimeError):
    pass


def _safe_text(value: object, limit: int = 500) -> str:
    text = str(value or "").replace("\n", " ")
    return _SECRET_PATTERN.sub(r"\1[REDACTED]", text)[:limit]


def _now() -> str:
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat()


def load_notification_state(path: Path) -> dict:
    if not path.exists():
        return {"version": STATE_VERSION, "updated_at": "", "incidents": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"通知状态无法读取，已停止以避免覆盖：{path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("incidents"), dict):
        raise ValueError(f"通知状态结构无效，已停止以避免覆盖：{path}")
    payload.setdefault("version", STATE_VERSION)
    payload.setdefault("updated_at", "")
    return payload


def save_notification_state(
    path: Path,
    payload: dict,
    *,
    updated_at: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["version"] = STATE_VERSION
    payload["updated_at"] = updated_at or _now()
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _incident_source(incident_id: str, incident: dict) -> str:
    source = str(incident.get("source") or "").strip()
    if source:
        return source
    if "::" in incident_id:
        return incident_id.split("::", 1)[1].strip()
    return ""


def _diagnosis_key(incident: dict) -> str:
    return str(
        incident.get("diagnosis_code")
        or incident.get("error_type")
        or incident.get("diagnosis")
        or incident.get("technical_reason")
        or ""
    ).strip()


def _notification_signature(
    incident_id: str,
    incident: dict,
    *,
    status: str | None = None,
) -> tuple[str, str, str]:
    return (
        _incident_source(incident_id, incident),
        str(status if status is not None else incident.get("status") or ""),
        _diagnosis_key(incident),
    )


def select_status_changes(queue: dict, state: dict) -> list[dict]:
    previous = state.get("incidents", {})
    queue_by_id = {
        str(incident.get("id") or ""): incident
        for incident in queue.get("incidents", [])
        if incident.get("id")
    }
    previous_signatures: set[tuple[str, str, str]] = set()
    for incident_id, previous_state in previous.items():
        previous_status = str(previous_state.get("status") or "")
        if previous_status not in NOTIFIABLE_STATUSES:
            continue
        incident = queue_by_id.get(str(incident_id), previous_state)
        previous_signatures.add(
            _notification_signature(
                str(incident_id),
                incident,
                status=previous_status,
            )
        )

    selected: list[dict] = []
    selected_signatures: set[tuple[str, str, str]] = set()
    for incident in queue.get("incidents", []):
        incident_id = str(incident.get("id") or "")
        status = str(incident.get("status") or "")
        if not incident_id or status not in NOTIFIABLE_STATUSES:
            continue
        if str(previous.get(incident_id, {}).get("status") or "") == status:
            continue
        signature = _notification_signature(incident_id, incident)
        if signature in previous_signatures or signature in selected_signatures:
            continue
        selected.append(incident)
        selected_signatures.add(signature)
    return sorted(
        selected,
        key=lambda item: (str(item.get("date")), str(item.get("source"))),
    )


def build_dingtalk_markdown(
    incidents: Iterable[dict],
    *,
    keyword: str,
    run_url: str = "",
    max_items: int = 30,
) -> tuple[str, str]:
    rows = list(incidents)
    title = f"{keyword}：{len(rows)} 条状态变化"
    lines = [
        f"## {keyword}",
        "",
        f"> 共检测到 **{len(rows)}** 条渠道状态变化",
        "",
    ]
    for item in rows[:max_items]:
        status = str(item.get("status") or "")
        label = STATUS_LABELS.get(status, status)
        diagnosis = _safe_text(
            item.get("last_error")
            or item.get("diagnosis")
            or item.get("technical_reason")
            or "未记录原因",
        )
        technical_reason = _safe_text(item.get("technical_reason"))
        occurred_at = _safe_text(
            item.get("failed_at")
            or item.get("last_attempt_at")
            or item.get("detected_at")
            or item.get("updated_at")
            or "-"
        )
        error_type = _safe_text(
            item.get("error_type") or item.get("diagnosis_code") or "-"
        )
        lines.extend(
            [
                f"### {label}｜{item.get('source')}",
                f"- 缺失日期：{item.get('date')}",
                f"- 发生/发现时间：{occurred_at}",
                f"- 错误类型：`{error_type}`",
                f"- 诊断：{diagnosis}",
                f"- 原始错误：{technical_reason}"
                if technical_reason and technical_reason != diagnosis
                else "- 原始错误：同上",
                f"- 处理状态：`{status}`",
                "",
            ]
        )
    if len(rows) > max_items:
        lines.extend([f"> 另有 {len(rows) - max_items} 条未展开，请查看恢复队列。", ""])
    if run_url:
        lines.extend([f"[查看 GitHub Actions 运行详情]({run_url})", ""])
    lines.append("修复后请运行 Channel Recovery，并填写渠道名和修复说明。")
    return title, "\n".join(lines)


def signed_webhook_url(
    webhook: str,
    secret: str = "",
    *,
    timestamp_ms: int | None = None,
) -> str:
    parsed = urlsplit(webhook)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (
        hostname == "dingtalk.com" or hostname.endswith(".dingtalk.com")
    ):
        raise ValueError("钉钉 Webhook 必须使用 dingtalk.com 域名的 HTTPS 地址")
    if not secret:
        return webhook
    timestamp = timestamp_ms or int(time.time() * 1000)
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"),
        string_to_sign,
        digestmod=hashlib.sha256,
    ).digest()
    encoded_signature = quote_plus(base64.b64encode(signature).decode("ascii"))
    separator = "&" if parsed.query else "?"
    return f"{webhook}{separator}timestamp={timestamp}&sign={encoded_signature}"


def send_dingtalk(
    webhook: str,
    *,
    secret: str,
    title: str,
    markdown: str,
    timeout: int = 15,
) -> None:
    target_url = signed_webhook_url(webhook, secret)
    body = json.dumps(
        {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": markdown},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        target_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    response_body = ""
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                response_body = response.read().decode("utf-8", errors="replace")
            break
        except HTTPError as exc:
            raise NotificationError(f"钉钉请求返回 HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise NotificationError("钉钉网络连接失败或超时") from exc
            time.sleep(2**attempt)
    try:
        result = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise NotificationError("钉钉返回了无法解析的响应") from exc
    error_code = result.get("errcode", result.get("code", 0))
    if error_code not in (0, "0", None):
        message = result.get("errmsg") or result.get("message") or "未知错误"
        raise NotificationError(f"钉钉拒绝消息：{error_code} {message}")


DingTalkSender = Callable[..., None]


def notify_dingtalk_changes(
    queue_path: Path,
    state_path: Path,
    *,
    webhook: str,
    secret: str = "",
    keyword: str = "渠道抓取告警",
    run_url: str = "",
    sender: DingTalkSender = send_dingtalk,
    timestamp: str | None = None,
) -> list[dict]:
    queue = load_queue(queue_path)
    state = load_notification_state(state_path)
    changes = select_status_changes(queue, state)
    if not changes:
        return []
    title, markdown = build_dingtalk_markdown(
        changes,
        keyword=keyword,
        run_url=run_url,
    )
    sender(
        webhook,
        secret=secret,
        title=title,
        markdown=markdown,
    )
    notified_at = timestamp or _now()
    incident_states = state.setdefault("incidents", {})
    for incident in changes:
        incident_states[str(incident["id"])] = {
            "status": str(incident.get("status") or ""),
            "source": str(incident.get("source") or ""),
            "diagnosis_code": _diagnosis_key(incident),
            "notified_at": notified_at,
        }
    save_notification_state(state_path, state, updated_at=notified_at)
    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渠道恢复状态外部通知")
    parser.add_argument(
        "--queue",
        type=Path,
        default=Path("logs/recovery-queue.json"),
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("logs/notification-state.json"),
    )
    parser.add_argument(
        "--keyword",
        default=os.environ.get("DINGTALK_KEYWORD") or "渠道抓取告警",
    )
    parser.add_argument("--run-url", default=os.environ.get("ALERT_RUN_URL", ""))
    parser.add_argument(
        "--test",
        action="store_true",
        help="忽略恢复队列并发送一条钉钉连接测试消息",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    webhook = os.environ.get("DINGTALK_WEBHOOK", "").strip()
    if not webhook:
        print("未配置 DINGTALK_WEBHOOK，跳过钉钉推送。")
        return 1 if args.test else 0
    secret = os.environ.get("DINGTALK_SECRET", "").strip()
    try:
        if args.test:
            test_title = f"{args.keyword}：连接测试"
            test_markdown = "\n".join(
                [
                    f"## {args.keyword}",
                    "",
                    "钉钉群机器人连接测试成功。",
                    "",
                    f"[查看 GitHub Actions 运行详情]({args.run_url})"
                    if args.run_url
                    else "本次测试由命令行触发。",
                ]
            )
            send_dingtalk(
                webhook,
                secret=secret,
                title=test_title,
                markdown=test_markdown,
            )
            print("钉钉连接测试消息发送成功。")
            return 0
        changes = notify_dingtalk_changes(
            args.queue,
            args.state,
            webhook=webhook,
            secret=secret,
            keyword=args.keyword,
            run_url=args.run_url,
        )
    except (NotificationError, ValueError) as exc:
        print(f"钉钉推送失败：{exc}")
        return 1
    if changes:
        print(f"钉钉推送成功，共 {len(changes)} 条状态变化。")
    else:
        print("没有新的渠道状态变化，无需推送。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
