"""Read only advertised official policy feeds and report whether they are usable.

This diagnostic never follows article links or adds a production source. A feed
whose robots status cannot be established is reported as blocked.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

USER_AGENT = "news-spider-policy-rss-probe/1.0"
FEEDS = {
    "人社部—政策法规": "http://www.mohrss.gov.cn/gkml/xxgk/rss.xml",
    "人社部—政策解读": "http://www.mohrss.gov.cn/gkml/zcjd/rss.xml",
    "国防科工局—政策法规": "https://www.sastind.gov.cn/n10086167/n10086221/rss.xml",
    "统计局—最新发布（对照）": "https://www.stats.gov.cn/sj/zxfb/rss.xml",
    "统计局—数据解读（对照）": "https://www.stats.gov.cn/sj/sjjd/rss.xml",
}


def _read(url: str) -> tuple[bytes, str, str]:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=12) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        actual = response.url
        if urlparse(actual).hostname != urlparse(url).hostname:
            raise ValueError("cross-host redirect")
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("response larger than 2 MB")
        return data, actual, response.headers.get("Content-Type", "")


def probe(url: str) -> dict[str, object]:
    origin = urlparse(url)
    robots_url = f"{origin.scheme}://{origin.netloc}/robots.txt"
    try:
        robots, _, content_type = _read(robots_url)
        if "html" in content_type.lower() or robots.lstrip().lower().startswith((b"<!doctype", b"<html")):
            return {"status": "robots_unavailable", "robots": robots_url,
                    "reason": "HTML returned instead of robots.txt"}
        parser = RobotFileParser()
        parser.parse(robots.decode("utf-8", errors="replace").splitlines())
        if not parser.can_fetch(USER_AGENT, url):
            return {"status": "robots_disallow", "robots": robots_url}
        data, actual, content_type = _read(url)
        if urlparse(actual).scheme != origin.scheme:
            return {"status": "redirect_needs_robots_check", "url": actual}
        root = ElementTree.fromstring(data)
        local = root.tag.rsplit("}", 1)[-1].lower()
        if local not in {"rss", "feed", "rdf"}:
            return {"status": "not_rss", "root": local, "url": actual}
        entries = [item for item in root.iter()
                   if item.tag.rsplit("}", 1)[-1].lower() in {"item", "entry"}]
        samples = []
        for item in entries[:5]:
            fields = {child.tag.rsplit("}", 1)[-1].lower(): (child.text or "").strip()
                      for child in item}
            samples.append({"title": fields.get("title", "")[:120],
                            "date": fields.get("pubdate") or fields.get("published") or fields.get("updated") or "",
                            "link": fields.get("link") or ""})
        return {"status": "feed", "url": actual, "content_type": content_type,
                "entries": len(entries), "samples": samples}
    except (HTTPError, URLError, TimeoutError, ValueError, ElementTree.ParseError) as exc:
        return {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"[:200]}


if __name__ == "__main__":
    for name, url in FEEDS.items():
        result = probe(url)
        print(json.dumps({"name": name, "advertised_url": url, **result}, ensure_ascii=False), flush=True)
