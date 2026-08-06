from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .rionews import split_rionews_workbook_by_date


DEFAULT_BASE_URL = "http://api.surbot.cn/data"
DEFAULT_SYSTEM_TYPE = "CATL-RIO"


def _config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _setting(config: dict[str, Any], key: str, env_name: str, default: str = "") -> str:
    return str(os.getenv(env_name) or config.get(key) or default).strip()


def _required_setting(config: dict[str, Any], key: str, env_name: str) -> str:
    value = _setting(config, key, env_name)
    if not value:
        raise ValueError(f"missing {env_name}")
    return value


def build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_system_token(
    session: requests.Session,
    base_url: str,
    username: str,
    password: str,
    system_type: str,
    timeout: int,
) -> str:
    response = session.get(
        f"{base_url.rstrip('/')}/users/get_system_token",
        params={"username": username, "password": password, "system_type": system_type},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 200 or not payload.get("data"):
        raise RuntimeError(f"RIOnews token request failed: {payload.get('message') or payload}")
    return str(payload["data"])


def download_export(
    session: requests.Session,
    base_url: str,
    token: str,
    output_file: Path,
    *,
    days: int,
    source_name: str = "",
    timeout: int,
) -> Path:
    params: dict[str, Any] = {"days": days}
    if source_name:
        params["source_name"] = source_name
    response = session.get(
        f"{base_url.rstrip('/')}/news/news_export",
        headers={"SYSTEM-TOKEN": token},
        params=params,
        stream=True,
        timeout=timeout,
    )
    if "json" in response.headers.get("Content-Type", "").lower():
        raise RuntimeError(f"RIOnews export failed: {response.json()}")
    response.raise_for_status()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_file.with_suffix(".xlsx.part")
    try:
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if chunk:
                    handle.write(chunk)
        if temporary.stat().st_size == 0:
            raise RuntimeError("RIOnews export returned an empty file")
        with temporary.open("rb") as handle:
            if handle.read(2) != b"PK":
                raise RuntimeError("RIOnews export is not a valid xlsx file")
        temporary.replace(output_file)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and split the RIOnews export")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--days", type=int)
    parser.add_argument("--daily-output-dir", type=Path)
    parser.add_argument("--target-date")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = _config(args.config)
        base_url = _setting(config, "base_url", "RIO_BASE_URL", DEFAULT_BASE_URL)
        username = _required_setting(config, "username", "RIO_USERNAME")
        password = _required_setting(config, "password", "RIO_PASSWORD")
        system_type = _setting(config, "system_type", "RIO_SYSTEM_TYPE", DEFAULT_SYSTEM_TYPE)
        source_name = _setting(config, "source_name", "RIO_SOURCE_NAME")
        days = args.days if args.days is not None else int(_setting(config, "days", "RIO_DAYS", "7"))
        timeout = int(_setting(config, "timeout_seconds", "RIO_TIMEOUT_SECONDS", "60"))
        output_dir = args.daily_output_dir or Path(
            os.getenv("RIONEWS_DAILY_DIR", ".runtime/rionews/daily")
        )
        target_date = (
            datetime.strptime(args.target_date, "%Y-%m-%d").date()
            if args.target_date
            else None
        )
        if days < 1:
            raise ValueError("days must be at least 1")

        session = build_session()
        token = get_system_token(
            session,
            base_url,
            username,
            password,
            system_type,
            timeout,
        )
        aggregate = output_dir.parent / "news_export.xlsx"
        download_export(
            session,
            base_url,
            token,
            aggregate,
            days=days,
            source_name=source_name,
            timeout=timeout,
        )
        outputs = split_rionews_workbook_by_date(
            aggregate,
            output_dir,
            required_date=target_date,
        )
        print(f"RIOnews daily workbooks prepared: {len(outputs)}")
        return 0
    except (OSError, ValueError, RuntimeError, requests.RequestException, json.JSONDecodeError) as exc:
        print(f"RIOnews preparation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
