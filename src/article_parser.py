from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from trafilatura import extract as extract_full_text

from .content_quality import assess_content
from .date_utils import date_from_url
from .http_client import HttpClient
from .load_sources import Source


ARTICLE_SELECTORS = (
    "article",
    ".article",
    ".article-detail",
    ".article-text",
    ".articleCont",
    ".article-cont",
    ".articleCon",
    ".article-con",
    ".entry-content",
    ".post-content",
    ".article-content",
    ".article-body",
    ".contentText",
    ".content-text",
    ".content_left",
    ".contentleft",
    ".detail-content",
    ".news-content",
    ".TRS_Editor",
    ".main-content",
    "#content",
    ".content",
    "main",
)

STRICT_SOURCE_ARTICLE_SELECTORS = {
    "interesting engineering": (
        ".body-content",
    ),
    "batteries news": (
        ".entry-content",
    ),
    "data center knowledge": (
        ".ArticleBase-BodyContent_Article",
    ),
    "pv magazine c&i pv": (
        ".pvmagazine-post-content .entry-content",
    ),
    "新华网科技": (
        ".main-left.left",
    ),
}

SOURCE_ARTICLE_SELECTORS = {
    "4c offshore": (
        "#NewsContent",
    ),
    "it之家": (
        "#paragraph",
    ),
    "科学网新闻": (
        "#content",
    ),
    "索比光伏": (
        ".detail-left-content-box",
        "article",
    ),
    "索比光伏-综合新闻": (
        ".detail-left-content-box",
        "article",
    ),
    "hydrogen tech world": (
        ".entry-content",
        ".post-content",
        ".article-content",
        "article",
    ),
    "electrive": (
        ".entry-content",
        ".post-content",
        ".article-content",
        "article",
    ),
    "battery tech online": (
        "[data-testid='article-body']",
        "[data-testid='body-content']",
        ".article-body",
        ".article__body",
        ".article-content",
        ".content-body",
        ".field--name-body",
        ".node__content",
        "main article",
    ),
    "volta foundation": (
        ".entry-content",
        ".post-content",
        ".article-content",
        "article",
    ),
}

BODY_BLOCK_TAGS = (
    "p",
    "div",
    "section",
    "article",
    "li",
    "blockquote",
    "pre",
    "h2",
    "h3",
    "h4",
    "td",
    "th",
    "figcaption",
)

REMOVE_SELECTORS = (
    "script",
    "style",
    "noscript",
    "iframe",
    "form",
    "nav",
    "aside",
    "header",
    "footer",
    ".share",
    ".social",
    ".newsletter",
    ".advert",
    ".advertisement",
    ".ad",
    ".ads",
    ".recommend",
    ".related",
    ".popular",
    ".breadcrumb",
    ".crumb",
    ".copyright",
    ".comment",
    ".pagination",
    ".pagecode",
    ".author",
    ".byline",
    ".tags",
    ".tag",
    ".sponsored",
    ".teaser",
    ".promo",
    ".signup",
    ".sign-up",
    ".event",
    ".events",
)

REMOVE_CLASS_ID_RE = re.compile(
    r"(?:^|[-_ ])(?:ad|ads|advert|banner|promo|recommend|related|popular|share|"
    r"social|comment|breadcrumb|crumb|footer|nav|sidebar)(?:$|[-_ ])",
    re.I,
)

BODY_STOP_MARKERS = (
    "\nPopular content\n",
    "\nRelated Articles\n",
    "\nRelated Stories\n",
    "\nAdvertisement\n",
    "\nAdvertisements\n",
    "\nShare\n",
    "\nSign up for Battery Technology newsletters\n",
    "\nWant more Battery Technology in your search results?\n",
    "\nYour Privacy Choices\n",
    "\nExplore more about Hymson",
    "\nThis is a sponsored article",
    "\n相关阅读\n",
    "\n相关推荐\n",
    "\n热门推荐\n",
    "\n更多新闻\n",
    "\n版权声明\n",
    "\n免责声明\n",
)

NON_BODY_LINE_RE = re.compile(
    r"^(?:"
    r"source|from|author|by|published|updated|editor|copyright|tags?|"
    r"share|newsletter|sign up|want more|your privacy choices|advertisement|sponsored|"
    r"来源|来自|作者|记者|编辑|责任编辑|发布时间|发布日期|时间|"
    r"关键词|标签|声明|版权|分享到|分享|打印|字号|阅读|浏览|"
    r"打开网易新闻 查看精彩图片|"
    r"上一篇|下一篇|相关|推荐|热门|更多"
    r")\b|^(?:来源|作者|编辑|责任编辑|发布时间|发布日期|时间|关键词|标签|版权|声明)[：:]",
    re.I,
)

STANDALONE_DOMAIN_RE = re.compile(r"^(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?$", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)
LABELED_DATE_RE = re.compile(
    r"(?:发布时间|发布日期|发稿时间|更新时间|日期)\s*[:：]\s*"
    r"(20\d{2}[年/\-.]\d{1,2}[月/\-.]\d{1,2}日?"
    r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)"
)
DATE_VALUE_RE = re.compile(
    r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}"
    r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)"
)
DATE_CONTAINER_SELECTORS = (
    ".time-source-address",
    ".article-time",
    ".publish-time",
    ".publish-date",
    ".pubtime",
    ".date",
    ".time",
)

MIN_PARAGRAPH_LENGTH = 8
BODY_END_LINE_KEYWORDS = (
    "版权声明",
    "免责声明",
    "版权归",
    "未经授权",
    "如需转载",
    "This content is protected by copyright",
    "If you want to cooperate",
    "This is a sponsored article",
    "If you'd like to inquire",
    "If you’d like to inquire",
    "Explore more about",
    "Sign up for Battery Technology newsletters",
    "Want more Battery Technology in your search results",
    "Your Privacy Choices",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def first_meta(soup: BeautifulSoup, names: tuple[str, ...]) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""

def resolve_canonical_url(url: str, candidate: str) -> str:
    if not candidate:
        return url
    candidate = candidate.strip()
    if re.search(r"\[[^\]]+\]|\{\{?.+?\}?\}", candidate):
        return url
    resolved = urljoin(url, candidate)
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return url
    return resolved

def extract_title(soup: BeautifulSoup) -> str:
    meta_title = first_meta(soup, ("og:title", "twitter:title"))
    if meta_title:
        return meta_title
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    if soup.title:
        return soup.title.get_text(" ", strip=True)
    return ""


def _iter_json_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _iter_json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_json_objects(child)


def extract_date(soup: BeautifulSoup) -> str:
    meta_date = first_meta(
        soup,
        (
            "article:published_time",
            "datePublished",
            "pubdate",
            "publishdate",
            "date",
            "dc.date",
            "DC.date.issued",
        ),
    )
    if meta_date:
        return meta_date
    time_tag = soup.find("time")
    if time_tag:
        return (time_tag.get("datetime") or time_tag.get_text(" ", strip=True)).strip()
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for node in _iter_json_objects(data):
            if isinstance(node, dict):
                value = node.get("datePublished") or node.get("dateCreated") or node.get("dateModified")
                if value:
                    return str(value).strip()
    labeled_date = LABELED_DATE_RE.search(soup.get_text(" ", strip=True))
    if labeled_date:
        return labeled_date.group(1).strip()
    published_date_node = soup.find(
        id=re.compile(r"(?:published|publish).*date", re.I)
    )
    if published_date_node:
        value = published_date_node.get_text(" ", strip=True)
        if re.fullmatch(r"\d{1,2}/\d{1,2}/20\d{2}", value):
            return value
    for selector in DATE_CONTAINER_SELECTORS:
        for node in soup.select(selector):
            date_value = DATE_VALUE_RE.search(node.get_text(" ", strip=True))
            if date_value:
                return date_value.group(1).strip()
    return ""


def normalize_source_date(value: str, source_name: str) -> str:
    """Normalize unambiguous publisher-specific numeric dates before global parsing."""
    if source_name.strip().lower() == "4c offshore":
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(20\d{2})", value.strip())
        if match:
            day, month, year = (int(part) for part in match.groups())
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return value
    return value


def extract_body(soup: BeautifulSoup, source_name: str = "") -> str:
    source_key = source_name.strip().lower()
    strict_selectors = STRICT_SOURCE_ARTICLE_SELECTORS.get(source_key, ())
    source_selectors = SOURCE_ARTICLE_SELECTORS.get(source_key, ())
    structured_body = extract_structured_body(soup)
    guarded_selectors = strict_selectors + source_selectors + ARTICLE_SELECTORS
    guarded_query = ",".join(guarded_selectors)
    for selector in REMOVE_SELECTORS:
        for tag in soup.select(selector):
            if tag.select_one(guarded_query):
                continue
            tag.decompose()
    for tag in list(soup.find_all(True)):
        if not getattr(tag, "attrs", None):
            continue
        if tag.select_one(guarded_query):
            continue
        class_id = " ".join(tag.get("class") or [])
        if tag.get("id"):
            class_id = f"{class_id} {tag.get('id')}"
        if class_id and REMOVE_CLASS_ID_RE.search(class_id):
            tag.decompose()

    candidates: list[tuple[int, str]] = []
    # A strict selector defines a hard content boundary. Mixing generic selectors
    # back in can select a larger page wrapper and pull in sidebars.
    selectors = strict_selectors or (source_selectors + ARTICLE_SELECTORS)
    for selector in selectors:
        for node in soup.select(selector):
            text = extract_node_body_text(node)
            if text:
                candidates.append((score_body_candidate(node, text), text))
    if structured_body:
        candidates.append(
            (
                len(structured_body)
                + len(structured_body.splitlines()) * 120,
                structured_body,
            )
        )
    if candidates:
        return trim_body_noise(max(candidates, key=lambda item: item[0])[1])
    if strict_selectors:
        return ""
    return trim_body_noise(clean_text(soup.get_text("\n", strip=True)))


def extract_node_body_text(node) -> str:
    paragraphs = []
    for tag in node.find_all(BODY_BLOCK_TAGS, recursive=True):
        if tag.find(BODY_BLOCK_TAGS):
            continue
        text = clean_text(tag.get_text("\n", strip=True))
        if is_body_line(text):
            paragraphs.append(text)
    if paragraphs:
        return clean_text("\n".join(paragraphs))

    lines = [
        line.strip()
        for line in clean_text(node.get_text("\n", strip=True)).splitlines()
        if is_body_line(line.strip())
    ]
    return clean_text("\n".join(lines))


def extract_structured_body(soup: BeautifulSoup) -> str:
    """Return the longest schema.org articleBody embedded in JSON-LD."""
    candidates: list[str] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _iter_json_objects(data):
            if not isinstance(node, dict):
                continue
            value = node.get("articleBody")
            if not isinstance(value, str) or not value.strip():
                continue
            text = clean_text(
                BeautifulSoup(value, "html.parser").get_text("\n", strip=True)
            )
            if is_body_line(text):
                candidates.append(text)
    return max(candidates, key=len, default="")


def extract_trafilatura_body(html: str, url: str = "") -> str:
    """Extract the complete main text with recall favored over brevity."""
    try:
        text = extract_full_text(
            html,
            url=url or None,
            output_format="txt",
            favor_recall=True,
            include_comments=False,
            include_tables=True,
            deduplicate=False,
        )
    except Exception:
        return ""
    return trim_body_noise(clean_text(text or ""))


def is_body_line(text: str) -> bool:
    if len(text) < MIN_PARAGRAPH_LENGTH:
        return False
    if EMAIL_RE.search(text):
        return False
    if STANDALONE_DOMAIN_RE.fullmatch(text):
        return False
    if NON_BODY_LINE_RE.search(text):
        return False
    if re.fullmatch(r"[\d\s:/.\-年月日时分秒]+", text):
        return False
    return True


def score_body_candidate(node, text: str) -> int:
    text_len = len(text)
    link_text_len = sum(len(link.get_text(" ", strip=True)) for link in node.find_all("a"))
    paragraph_count = len([line for line in text.splitlines() if len(line.strip()) >= MIN_PARAGRAPH_LENGTH])
    link_penalty = min(link_text_len, text_len)
    return text_len + paragraph_count * 120 - link_penalty * 2


def trim_body_noise(text: str) -> str:
    text = clean_text(text)
    for marker in BODY_STOP_MARKERS:
        index = text.find(marker)
        if index > 0:
            text = text[:index]
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(keyword in stripped for keyword in BODY_END_LINE_KEYWORDS):
            break
        if is_body_line(stripped):
            lines.append(stripped)
    return clean_text("\n".join(lines))


def parse_article_html(html: str, url: str, source: Source, crawled_at: Optional[str] = None) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    canonical = resolve_canonical_url(url, first_meta(soup, ("og:url",)))
    link = soup.find("link", rel=lambda value: value and "canonical" in value)
    if link and link.get("href"):
        canonical = resolve_canonical_url(url, link["href"])
    requested_url_date = date_from_url(url)
    canonical_url_date = date_from_url(canonical)
    if requested_url_date and canonical_url_date and requested_url_date != canonical_url_date:
        canonical = url

    url_date = date_from_url(canonical) or date_from_url(url)
    published_at = (
        url_date.isoformat()
        if url_date
        else normalize_source_date(extract_date(soup), source.name)
    )
    title = extract_title(soup)

    selector_body = extract_body(soup, source.name)
    full_text_body = extract_trafilatura_body(html, canonical)
    source_key = source.name.strip().lower()
    if source_key in STRICT_SOURCE_ARTICLE_SELECTORS and selector_body:
        content = selector_body
        extraction_method = "dom_or_structured_full_text"
    elif len(full_text_body) > len(selector_body):
        content = full_text_body
        extraction_method = "trafilatura_full_text"
    else:
        content = selector_body
        extraction_method = "dom_or_structured_full_text"
    content_status, content_issue = assess_content(
        content,
        extraction_method=extraction_method,
    )

    return {
        "title": title,
        "published_at": published_at,
        "content": content,
        "content_status": content_status,
        "content_issue": content_issue,
        "content_extraction": extraction_method,
        "url": canonical,
        "source_name": source.name,
        "domain": source.domain,
        "sub_domain": source.sub_domain,
        "crawled_at": crawled_at or utc_now_iso(),
    }


def fetch_and_parse_article(client: HttpClient, url: str, source: Source) -> Optional[dict]:
    result = client.get(url, allow_non_html=False)
    if not result:
        return None
    article = parse_article_html(result.text, url, source)
    if article.get("content_issue") == "access_challenge":
        return None
    if not article["title"] and not article["content"]:
        return None
    return article
