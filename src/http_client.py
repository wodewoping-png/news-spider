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


@dataclass
class FetchResult:
    url: str
    text: str
    status_code: int
    content_type: str


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
                response = self.session.get(robots_url, timeout=self.timeout)
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

    def get(self, url: str, *, allow_non_html: bool = True) -> Optional[FetchResult]:
        if self.respect_robots and not self.robots.can_fetch(url):
            logging.warning("Blocked by robots.txt: %s", url)
            return None

        time.sleep(self.sleep_seconds)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
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
        return FetchResult(
            url=response.url,
            text=response_text,
            status_code=response.status_code,
            content_type=content_type,
        )
