from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .catalog import GOVERNMENT_SITES, CandidateSite
from .ministry_catalog import MINISTRY_SITES, READY_MINISTRY_SITES


USER_AGENT = "GovernmentAnnouncementCandidate/0.1 (manual-review; low-rate; text-only)"


def preferred_encoding(declared: str | None, apparent: str | None) -> str:
    value = (declared or "").strip()
    if not value or value.lower() in {"iso-8859-1", "latin-1"}:
        return (apparent or "utf-8").strip() or "utf-8"
    return value


def decode_body(body: bytes, encoding: str = "") -> str:
    for candidate in (encoding, "utf-8", "gb18030"):
        if not candidate:
            continue
        try:
            return body.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    return session


def _fetch(session: requests.Session, url: str, *, timeout: float, delay: float) -> tuple[dict[str, Any], bytes]:
    time.sleep(max(1.25, delay))
    started = time.monotonic()
    try:
        response = session.get(url, timeout=timeout, allow_redirects=False)
        body = response.content
        return ({
            "requested_url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "encoding": preferred_encoding(response.encoding, response.apparent_encoding),
            "body_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }, body)
    except requests.RequestException as exc:
        return ({
            "requested_url": url,
            "error": type(exc).__name__,
            "message": str(exc),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }, b"")


def _robots_decision(text: str, targets: tuple[str, ...]) -> dict[str, bool]:
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    return {url: parser.can_fetch(USER_AGENT, url) for url in targets}


def _summarize_html(text: str, base_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(text, "html.parser")
    links: list[dict[str, str]] = []
    base_host = urlparse(base_url).netloc.lower()
    for anchor in soup.select("a[href]"):
        url = urljoin(base_url, str(anchor.get("href", "")))
        if urlparse(url).netloc.lower() == base_host and re.search(
            r"(?:/20\d{4}/|/art/20\d{2}/|t20\d{6}_)", urlparse(url).path
        ):
            links.append({
                "title": " ".join(anchor.get_text(" ", strip=True).split())[:200],
                "url": url,
            })
    selectors: dict[str, int] = {}
    for node in soup.find_all(True):
        if not (node.get("id") or node.get("class")):
            continue
        signature = node.name
        if node.get("id"):
            signature += f"#{node['id']}"
        if node.get("class"):
            signature += "." + ".".join(node.get("class", []))
        selectors[signature] = selectors.get(signature, 0) + 1
    return {
        "document_title": soup.title.get_text(" ", strip=True) if soup.title else "",
        "article_links": links[:80],
        "selector_inventory": dict(sorted(selectors.items(), key=lambda x: (-x[1], x[0]))[:80]),
    }


def probe_site(
    session: requests.Session,
    site: CandidateSite,
    output_dir: Path,
    *,
    timeout: float,
    sleep_seconds: float,
    include_feeds: bool = False,
) -> dict[str, Any]:
    del include_feeds
    site_dir = output_dir / site.slug
    site_dir.mkdir(parents=True, exist_ok=True)
    targets = site.listing_urls + site.sample_urls
    robots_url = f"https://{urlparse(site.primary_listing_url).netloc}/robots.txt"
    robots_response, robots_body = _fetch(session, robots_url, timeout=timeout, delay=sleep_seconds)
    robots_text = decode_body(robots_body, robots_response.get("encoding", ""))
    status = robots_response.get("status_code")
    if status == 200:
        decisions: dict[str, bool | None] = _robots_decision(robots_text, targets)
        robots_status = "found"
    elif status == 404:
        decisions = {url: True for url in targets}
        robots_status = "not_found"
    else:
        decisions = {url: None for url in targets}
        robots_status = "unavailable"
    record: dict[str, Any] = {
        "candidate": asdict(site),
        "robots": {"response": robots_response, "analysis": {"status": robots_status, "decisions": decisions}},
        "pages": [],
        "feeds": [],
    }
    for index, url in enumerate(targets, start=1):
        allowed = decisions[url]
        if allowed is not True:
            record["pages"].append({
                "url": url,
                "skipped": "robots_disallow" if allowed is False else "robots_unavailable",
            })
            continue
        response, body = _fetch(session, url, timeout=timeout, delay=sleep_seconds)
        page: dict[str, Any] = {"url": url, "response": response}
        if response.get("status_code") == 200 and body:
            text = decode_body(body, response.get("encoding", ""))
            kind = "listing" if url in site.listing_urls else "sample"
            filename = f"{kind}-{index:02d}-{hashlib.sha256(url.encode()).hexdigest()[:10]}.html"
            (site_dir / filename).write_text(text, encoding="utf-8")
            page["raw_file"] = str((site_dir / filename).relative_to(output_dir))
            page["html"] = _summarize_html(text, response.get("final_url", url))
        record["pages"].append(page)
    return record


def markdown_summary(evidence: dict[str, Any]) -> str:
    lines = ["# Government announcement compliance/DOM probe", "", f"Generated: {evidence['generated_at']}", f"User-Agent: `{evidence['user_agent']}`", ""]
    for site in evidence["sites"]:
        candidate, robots = site["candidate"], site["robots"]
        lines.extend([f"## {candidate['source_name']}", ""])
        lines.append(f"- robots: `{robots['response'].get('status_code', robots['response'].get('error', 'unknown'))}`; decision `{robots['analysis'].get('status')}`")
        ok = [p for p in site["pages"] if p.get("response", {}).get("status_code") == 200]
        lines.append(f"- pages HTTP 200: {len(ok)}/{len(site['pages'])}")
        for page in ok:
            html = page.get("html", {})
            lines.extend([f"- page: {page['url']}", f"  - title: {html.get('document_title', '')}", f"  - article links: {len(html.get('article_links', []))}"])
        skipped = [p for p in site["pages"] if p.get("skipped")]
        if skipped:
            lines.append(f"- skipped: {[(p['url'], p['skipped']) for p in skipped]}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Low-rate government announcement probe.")
    parser.add_argument("--output-dir", type=Path, default=Path("tmp/government-announcement-evidence"))
    parser.add_argument("--delay", type=float, default=1.25)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--catalog", choices=("initial", "ministries", "ready", "all"), default="initial")
    args = parser.parse_args()
    sites = {"initial": GOVERNMENT_SITES, "ministries": MINISTRY_SITES, "ready": READY_MINISTRY_SITES, "all": GOVERNMENT_SITES + MINISTRY_SITES}[args.catalog]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "scope": "candidate evidence only; no production integration",
        "sites": [probe_site(make_session(), site, args.output_dir, timeout=args.timeout, sleep_seconds=max(1.25, args.delay)) for site in sites],
    }
    (args.output_dir / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "SUMMARY.md").write_text(markdown_summary(evidence), encoding="utf-8")
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
