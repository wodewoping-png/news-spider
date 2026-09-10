from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from .probe import decode_body, preferred_encoding
from .base import ContractViolation

from .scrapers import (
    GovernmentDocumentScraper,
    MiitPublicNoticesScraper,
    NeaDocumentScraper,
    StaticMinistryScraper,
    SCRAPERS,
)


USER_AGENT = "GovernmentAnnouncementCandidate/0.1 (manual-review; low-rate; text-only)"


class ComplianceClient:
    def __init__(self, *, delay: float = 1.25, timeout: float = 20.0):
        self.delay = max(1.25, delay)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.5",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        self._last_request = 0.0
        self._robots: dict[str, tuple[str, RobotFileParser]] = {}

    def _request(self, url: str, *, params: dict[str, str] | None = None) -> requests.Response:
        remaining = self.delay - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        response = self.session.get(
            url, params=params, timeout=self.timeout, allow_redirects=False
        )
        self._last_request = time.monotonic()
        if response.status_code in {403, 429}:
            raise ContractViolation(f"site refused candidate request: HTTP {response.status_code} {url}")
        if 300 <= response.status_code < 400:
            raise ContractViolation(f"unexpected redirect: HTTP {response.status_code} {url}")
        response.raise_for_status()
        return response

    def _gate(self, host: str) -> tuple[str, RobotFileParser]:
        if host in self._robots:
            return self._robots[host]
        robots_url = f"https://{host}/robots.txt"
        remaining = self.delay - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        response = self.session.get(robots_url, timeout=self.timeout, allow_redirects=False)
        self._last_request = time.monotonic()
        if response.status_code not in {200, 404}:
            raise ContractViolation(f"robots unavailable: HTTP {response.status_code} {robots_url}")
        parser = RobotFileParser()
        if response.status_code == 404:
            status, text = "NOT_FOUND", "User-agent: *\nDisallow:"
        else:
            status = "FOUND"
            text = decode_body(
                response.content,
                preferred_encoding(response.encoding, response.apparent_encoding),
            )
        parser.parse(text.splitlines())
        self._robots[host] = (status, parser)
        return self._robots[host]

    def get(
        self,
        scraper: GovernmentDocumentScraper,
        url: str,
        *,
        detail: bool = False,
        params: dict[str, str] | None = None,
    ) -> tuple[requests.Response, str]:
        guarded = scraper.guard_url(url, detail=detail)
        robots_status, parser = self._gate(urlparse(guarded).netloc)
        if not parser.can_fetch(USER_AGENT, guarded):
            raise ContractViolation(f"robots disallow: {guarded}")
        response = self._request(guarded, params=params)
        final = scraper.guard_url(response.url, detail=detail)
        if urlparse(final).netloc not in scraper.allowed_hosts:
            raise ContractViolation(f"off-contract response origin: {final}")
        return response, robots_status


def _decoded(response: requests.Response) -> str:
    return decode_body(
        response.content,
        preferred_encoding(response.encoding, response.apparent_encoding),
    )


def run_site(
    scraper: GovernmentDocumentScraper, client: ComplianceClient
) -> dict[str, object]:
    result: dict[str, object] = {
        "source_id": scraper.source_id,
        "source_name": scraper.source_name,
        "production_enabled": False,
        "status": "failed",
    }
    try:
        if isinstance(scraper, NeaDocumentScraper):
            response, robots_status = client.get(scraper, scraper.data_url)
            items = scraper.parse_listing_json(response.content, response.url)
        elif isinstance(scraper, MiitPublicNoticesScraper):
            response, robots_status = client.get(
                scraper, scraper.data_url, params=scraper.query_params
            )
            items = scraper.parse_api_response(response.content, response.url)
        elif isinstance(scraper, StaticMinistryScraper):
            response, robots_status = client.get(scraper, scraper.listing_url)
            items = scraper.parse_listing(_decoded(response), response.url)
        else:
            raise TypeError(type(scraper).__name__)
        if len(items) < 2:
            raise ContractViolation(f"expected at least two list items, got {len(items)}")
        if not scraper.fetch_detail:
            result.update(
                {
                    "status": "passed_metadata_only",
                    "robots_status": robots_status,
                    "listing_count": len(items),
                    "listing_sample": [item.to_dict() for item in items[:2]],
                    "assertions": {
                        "https_approved_origins_only": True,
                        "detail_not_requested": True,
                        "attachments_not_downloaded": True,
                        "production_disabled": True,
                    },
                }
            )
            return result
        detail_response, _ = client.get(scraper, items[0].url, detail=True)
        article = scraper.parse_detail(_decoded(detail_response), detail_response.url)
        result.update(
            {
                "status": "passed",
                "robots_status": robots_status,
                "listing_count": len(items),
                "listing_sample": [item.to_dict() for item in items[:2]],
                "article": {
                    "title": article.title,
                    "url": article.platform_url,
                    "published_at": article.platform_published_at.isoformat(),
                    "source": article.source,
                    "content_chars": len(article.content),
                    "content_preview": article.content[:500],
                },
                "assertions": {
                    "https_same_origin_only": True,
                    "detail_text_nonempty": bool(article.content),
                    "attachments_not_downloaded": True,
                    "images_not_copied": True,
                    "production_disabled": article.production_enabled is False,
                },
            }
        )
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded live test for government candidates.")
    parser.add_argument("--site", action="append", choices=sorted(SCRAPERS), default=[])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/government-announcement-live-test.json"),
    )
    parser.add_argument("--delay", type=float, default=1.25)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    selected = args.site or list(SCRAPERS)
    client = ComplianceClient(delay=args.delay, timeout=args.timeout)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "standalone candidates; no production integration",
        "compliance": {
            "full_text": "verified official administrative documents only",
            "attachments": "never downloaded",
            "ndrc_public_notices": "HOLD: robots.txt returned HTTP 403",
            "miit_policy_database": "HOLD: stable minimal listing contract pending",
            "moa_public_information": "HOLD: robots.txt explicitly disallows /",
            "mee_public_notices": "HOLD: robots.txt redirects to a 404 page",
            "mwr_notices": "HOLD: TLS/robots result unavailable",
            "mof_announcements": "HOLD: stable detail contract pending",
            "mnr_notices": "metadata only: current details use a different subdomain/template",
        },
        "sites": [run_site(SCRAPERS[name], client) for name in selected],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)
    return 0 if all(str(site["status"]).startswith("passed") for site in report["sites"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
