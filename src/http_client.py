from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_USER_AGENT = (
    "DailyNewsSpider/0.1 "
    "(respectful research crawler; contact: update-user-agent-in-config)"
)
SCIENCENET_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0 Safari/537.36"
)

ACCESS_CHALLENGE_SIGNATURE_GROUPS = (
    ("cf_app_waf", "requestinfo"),
    ("cf-chl-", "challenge-platform"),
    ("checking your browser", "enable javascript and cookies"),
    ("verify you are human", "cloudflare"),
)


def is_access_challenge_html(value: str) -> bool:
    """Detect access-control interstitials that returned HTTP 200 as if they were pages."""
    probe = str(value or "")[:100_000].lower()
    return any(all(marker in probe for marker in group) for group in ACCESS_CHALLENGE_SIGNATURE_GROUPS)


def request_headers_for_url(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, str]:
    """Return narrow site-specific headers when the default crawler UA is blocked."""
    if user_agent != DEFAULT_USER_AGENT:
        return {}
    hostname = (urlparse(url).hostname or "").lower()
    if hostname == "sciencenet.cn" or hostname.endswith(".sciencenet.cn"):
        return {"User-Agent": SCIENCENET_BROWSER_USER_AGENT}
    return {}


@dataclass
class FetchResult:
    url: str
    text: str
    status_code: int
    content_type: str


class RequiredFetchError(RuntimeError):
    """Raised when a required authenticated/resource fetch cannot be completed."""


class RobotsCache:
    def __init__(self, session: requests.Session, user_agent: str, timeout: int) -> None:
        self.session = session
        self.user_agent = user_agent
        self.timeout = timeout
        self._cache: dict[str, RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        root = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._cache.get(root)
        if parser is None:
            parser = RobotFileParser()
            robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
            parser.set_url(robots_url)
            try:
                response = self.session.get(
                    robots_url,
                    timeout=self.timeout,
                    headers=request_headers_for_url(robots_url, self.user_agent),
                )
                if response.status_code >= 400:
                    logging.warning("robots.txt unavailable for %s: HTTP %s", root, response.status_code)
                    parser.parse([])
                else:
                    parser.parse(response.text.splitlines())
            except requests.RequestException as exc:
                logging.warning("robots.txt fetch failed for %s: %s", root, exc)
                parser.parse([])
            self._cache[root] = parser

        return parser.can_fetch(self.user_agent, url)


class HttpClient:
    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = 20,
        sleep_seconds: float = 1.5,
        respect_robots: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.respect_robots = respect_robots
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
            }
        )

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.robots = RobotsCache(self.session, user_agent, timeout)

    def get(
        self,
        url: str,
        *,
        allow_non_html: bool = True,
        auth: tuple[str, str] | None = None,
        required: bool = False,
    ) -> Optional[FetchResult]:
        if self.respect_robots and not self.robots.can_fetch(url):
            if required:
                raise RequiredFetchError(f"Required fetch blocked by robots.txt: {url}")
            logging.warning("Blocked by robots.txt: %s", url)
            return None

        time.sleep(self.sleep_seconds)
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                headers=request_headers_for_url(url, self.user_agent),
                auth=auth,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            if required:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                reason = f"HTTP {status_code}" if status_code else type(exc).__name__
                raise RequiredFetchError(
                    f"Required fetch failed: {url} ({reason})"
                ) from exc
            logging.warning("Fetch failed: %s (%s)", url, exc)
            return None

        content_type = response.headers.get("content-type", "")
        if not allow_non_html and "html" not in content_type.lower():
            logging.info("Skip non-html response: %s (%s)", url, content_type)
            return None

        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding
        response_text = response.text
        stripped_text = response_text.strip()
        if not stripped_text:
            logging.warning("Empty response body: %s", response.url)
            return None
        lowered_probe = stripped_text[:2000].lower()
        if (
            "<h1>404 not found</h1>" in lowered_probe
            or "页面不存在" in stripped_text[:2000]
        ):
            logging.warning("Soft 404 response: %s", response.url)
            return None
        if is_access_challenge_html(response_text):
            logging.warning("Access challenge response: %s", response.url)
            return None
        return FetchResult(
            url=response.url,
            text=response_text,
            status_code=response.status_code,
            content_type=content_type,
        )
