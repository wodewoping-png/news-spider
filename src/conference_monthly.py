"""Monthly conference snapshots from the NCSTI calendar and Materials Today listings."""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .http_client import HttpClient

NCSTI_URL = "https://www.ncsti.gov.cn/kjdt/"
INEW_URL = "https://mtl.inew.cn/academic/conferences?lang=zh"
CALLBACK = "news_spider_callback"
HEADERS = ("来源", "会议名称", "开始日期", "结束日期", "地点", "会议详情", "会议简介", "采集月份")


def decode_jsonp(text: str) -> object:
    match = re.fullmatch(rf"\s*{CALLBACK}\((.*)\);?\s*", text, re.S)
    if not match:
        raise ValueError("NCSTI calendar returned invalid JSONP")
    return json.loads(match.group(1))


def request_jsonp(client: HttpClient, path: str, params: dict[str, str]) -> object:
    from urllib.parse import urlencode
    url = urljoin(NCSTI_URL, path) + "?" + urlencode({**params, "callback": CALLBACK})
    response = client.get(url)
    if not response:
        raise RuntimeError(f"NCSTI calendar request failed: {path}: {client.last_failure_reason}")
    return decode_jsonp(response.text)


def month_after(month: date) -> date:
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def ncsti_conferences(client: HttpClient, month: date) -> list[dict]:
    """Read days with channel 79, then query each day's conference records."""
    events: dict[str, dict] = {}
    for first in (month, month_after(month)):
        days = request_jsonp(client, "/kw/meeting/cale", {"year": str(first.year), "month": str(first.month)})
        if not isinstance(days, list):
            raise ValueError("NCSTI calendar day list is not an array")
        event_days = sorted({item["datetime"] for item in days if isinstance(item, dict)
                             and str(item.get("ChannelId")) == "79"
                             and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(item.get("datetime", "")))
                             and item["datetime"].startswith(first.strftime("%Y-%m"))})
        for day in event_days:
            page = 1
            while True:
                result = request_jsonp(client, "/kw/meeting/query", {
                    "channelId": "79", "datetime": day, "marktime": "", "order": "", "curpage": str(page),
                })
                if not isinstance(result, dict) or not isinstance(result.get("resultList"), list):
                    raise ValueError(f"NCSTI meeting list is invalid: {day}")
                if int(result.get("curpage", page)) != page:
                    raise ValueError(f"NCSTI pagination did not advance: {day} page {page}")
                for item in result["resultList"]:
                    if not isinstance(item, dict) or str(item.get("ChannelId")) != "79":
                        continue
                    event_day = str(item.get("datetime", ""))[:10]
                    if event_day != day:
                        continue
                    url = str(item.get("DOCPUBURL") or "").strip()
                    parsed = urlparse(url)
                    if parsed.scheme != "https" or parsed.hostname != "www.ncsti.gov.cn":
                        continue
                    title = str(item.get("doctitle") or "").strip()
                    if not title:
                        continue
                    content = BeautifulSoup(str(item.get("content") or ""), "html.parser").get_text(" ", strip=True)
                    events[url] = {"来源": "北京国际科技创新中心—会议日历", "会议名称": title,
                                   "开始日期": event_day, "结束日期": "", "地点": str(item.get("place") or "").strip(),
                                   "会议详情": url, "会议简介": content[:1000], "采集月份": month.strftime("%Y-%m")}
                if page >= int(result.get("pageCount", 1)):
                    break
                page += 1
                if page > 100:
                    raise ValueError("NCSTI meeting pagination exceeded 100 pages")
    return list(events.values())


def inew_conferences(client: HttpClient, month: date) -> list[dict]:
    result = client.get(INEW_URL)
    if not result:
        raise RuntimeError(f"mtl.inew.cn conference listing unavailable: {client.last_failure_reason}")
    soup = BeautifulSoup(result.text, "html.parser")
    events: dict[str, dict] = {}
    for link in soup.select("a[href]"):
        url = urljoin(result.url, link.get("href", ""))
        parsed = urlparse(url)
        if (parsed.hostname != "mtl.inew.cn" or
                not re.match(r"^/academic/conferences?/[^/?#]+", parsed.path)):
            continue
        title = link.get_text(" ", strip=True) or link.get("title", "").strip()
        if len(title) < 6:
            continue
        nearby = link.parent.get_text(" ", strip=True) if link.parent else ""
        dates = re.findall(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?", nearby)
        from .date_utils import parse_published_datetime
        start = parse_published_datetime(dates[0]).date().isoformat() if dates and parse_published_datetime(dates[0]) else ""
        end = parse_published_datetime(dates[1]).date().isoformat() if len(dates) > 1 and parse_published_datetime(dates[1]) else ""
        if not start or not (month.strftime("%Y-%m") <= start[:7] <= month_after(month).strftime("%Y-%m")):
            continue
        events[url] = {"来源": "mtl.inew.cn—学术会议", "会议名称": title, "开始日期": start,
                       "结束日期": end, "地点": "", "会议详情": url,
                       "会议简介": nearby[:1000], "采集月份": month.strftime("%Y-%m")}
    if not events:
        raise ValueError("mtl.inew.cn returned no verifiable conference links; check access or page format")
    return list(events.values())


def collect(month: date, root: Path, client: HttpClient) -> dict:
    destination = root / month.strftime("%Y-%m")
    destination.mkdir(parents=True, exist_ok=True)
    events: list[dict] = []
    statuses = []
    for name, url, reader in (("mtl.inew.cn—学术会议", INEW_URL, inew_conferences),
                              ("北京国际科技创新中心—会议日历", NCSTI_URL, ncsti_conferences)):
        try:
            found = reader(client, month)
            events.extend(found)
            statuses.append({"source": name, "url": url, "status": "ok", "count": len(found), "error": ""})
        except Exception as exc:
            statuses.append({"source": name, "url": url, "status": "failed", "count": 0, "error": str(exc)[:500]})
    events.sort(key=lambda row: (row["开始日期"] or "9999", row["来源"], row["会议名称"]))
    with (destination / "会议清单.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(events)
    index = {"month": month.strftime("%Y-%m"), "coverage_end": month_after(month).strftime("%Y-%m"),
             "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
             "count": len(events), "sources": statuses}
    (destination / "索引.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="每月抓取本月和下月的学术会议")
    parser.add_argument("--month", type=lambda value: date.fromisoformat(value + "-01"),
                        default=datetime.now(ZoneInfo("Asia/Shanghai")).date().replace(day=1))
    parser.add_argument("--output-dir", type=Path, default=Path("data/conferences"))
    args = parser.parse_args(argv)
    result = collect(args.month, args.output_dir, HttpClient(sleep_seconds=1.5, respect_robots=True))
    print(json.dumps({"month": result["month"], "count": result["count"], "sources": result["sources"]}, ensure_ascii=False))
    return 1 if any(source["status"] != "ok" for source in result["sources"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
