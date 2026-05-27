# Daily News Spider

一个可在 GitHub Actions 中每天定时运行的 Python 网页新闻抓取项目。它会读取 Excel 信息源清单，优先发现 RSS / Atom；如果没有可用 RSS，则调用对应来源的 scraper 模块。

当前默认输入文件是 `sources.xlsx`。本目录里的原始表格 `news web.xlsx` 已复制为 `sources.xlsx`，后续只维护 `sources.xlsx` 即可。

`sources.xlsx` 已合并 `else/news-search-main` 项目中的每日抓取渠道。当前共有 46 条来源记录，其中 36 条会进入每日抓取流程，10 条因公众号、无法访问、需订阅或空链接而默认跳过。

## 采集字段

每篇新闻保存到 `data/articles.jsonl`，并同步导出带运行日期的 CSV，例如 `data/articles-2026-05-27.csv`：

- `title`: 新闻标题
- `published_at`: 发布日期
- `content`: 正文内容
- `url`: 原文 URL
- `source_name`: 来源名称
- `domain`: 主干领域
- `sub_domain`: 细分领域
- `crawled_at`: 抓取时间，UTC ISO 格式

## 更新 sources.xlsx

Excel 表头必须包含：

`网站/来源`、`媒体类型`、`主干领域`、`细分领域`、`更新频率`、`内容简介`、`备注`、`链接`

跳过规则：

- `备注` 包含 `公众号`
- `备注` 包含 `无法访问`
- `备注` 包含 `需邮箱订阅` 或 `邮箱订阅`
- `备注` 包含 `不适合`
- `链接` 为空

这些来源不会抓取，但会写入日志，例如 `logs/daily-news.log`。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.main --sources sources.xlsx
```

常用参数：

```powershell
python -m src.main --sources "news web.xlsx" --limit-per-source 10 --sleep 2
```

默认会遵守 robots.txt，并设置 User-Agent、超时、重试和请求间隔。若确需调试 robots 规则，可临时使用：

```powershell
python -m src.main --ignore-robots
```

## GitHub Actions 运行

workflow 文件位于 `.github/workflows/daily-news.yml`。

- 每天 UTC 14:00 自动运行一次，约等于北京时间 22:00。
- 支持在 GitHub 页面手动点击 `workflow_dispatch` 运行。
- 运行后会上传 `data/` 和 `logs/` 为 artifact。
- 如果 `data/` 或 `logs/` 有变化，会自动提交回仓库。

首次放入 GitHub 仓库后，请确认仓库 `Settings -> Actions -> General -> Workflow permissions` 允许 `Read and write permissions`。

## 抓取逻辑

1. 读取 `sources.xlsx`。
2. 根据备注和链接判断是否跳过。
3. 访问来源页面，查找 `<link type="application/rss+xml">`、Atom/RSS alternate 链接。
4. 如果 `备注` 中写有 `RSS: https://...`，优先使用该指定 RSS；这用于承接 `news-search-main` 中已有的 RSS / Google News RSS 配置。
5. 继续尝试常见 RSS 路径：`/feed`、`/rss`、`/atom.xml`、`/feed.xml`、`/rss.xml`、`/index.xml`。
6. RSS 可用时，读取 RSS 的标题、日期、URL，再进入文章页解析正文。
7. RSS 不可用时，调用 `src/scrapers/` 中对应来源 scraper。
8. 以 URL 去重，不重复保存已存在文章。
9. 输出 `data/articles.jsonl` 和带运行日期的 CSV，例如 `data/articles-2026-05-27.csv`。

## 新增一个网站 scraper

每个来源建议一个独立模块。示例：

```python
# src/scrapers/example_site.py
from __future__ import annotations

from .generic import GenericListingScraper


class ExampleSiteScraper(GenericListingScraper):
    link_selectors = (
        "article h2 a[href]",
        ".news-list a[href]",
    )
```

然后在 `src/scrapers/__init__.py` 注册：

```python
from .example_site import ExampleSiteScraper

SCRAPER_REGISTRY = {
    "example site": ExampleSiteScraper,
}
```

如果网页是动态加载：

1. 先打开浏览器开发者工具，查看 Network / Fetch/XHR。
2. 找到返回文章列表的接口 URL、分页参数、返回字段。
3. 在独立 scraper 中请求该接口。
4. 如果无法确定接口，请在 scraper 中记录 `TODO` 日志，说明需要人工提供列表接口、文章链接 CSS 选择器或 HTML 样例。

## 已实现的示例 scraper

已为表格中的前几个网页新闻源准备独立模块：

- `electrive`: `src/scrapers/electrive.py`
- `Batteries International`: `src/scrapers/batteries_international.py`
- `Volta Foundation`: `src/scrapers/volta.py`
- `Battery Tech Online`: `src/scrapers/batterytechonline.py`
- `Supply Chain Digital`: `src/scrapers/supply_chain_digital.py`
- `Electrek`: `src/scrapers/electrek.py`
- `pv magazine`: `src/scrapers/pv_magazine.py`

这些模块先使用来源页面的文章链接选择器，再进入详情页使用通用正文解析器。对 WordPress 或公开 RSS 支持良好的网站，运行时通常会优先走 RSS。

## 从 news-search-main 补充的渠道

已从 `else/news-search-main/news-search-main/carbon_spider/configs/sites.yaml` 补入缺失渠道，包括 ESS News、Ammonia Energy Association、H2 View、Hydrogen Tech World、BloombergNEF Press、网易知光谷、中国核电信息网、中国电力新闻网、科学网新闻、新华网科技、国际太阳能光伏网、Renewables Now 等。对于同一品牌但抓取入口不同的来源，例如 `pv magazine C&I PV`、`MIT Technology Review Climate`、`索比光伏-综合新闻`、`中国新能源网-新闻`，保留为独立行，便于后续按频道维护 scraper。

## 当前需要人工确认的来源

根据 `sources.xlsx` 备注，以下来源默认跳过：

- `batteries news`: 备注为公司无法访问
- `Battery Council International`: 备注为需邮箱订阅
- `中粉固态电池`、`起点钠电`、`能源学人`、`钙钛矿工厂`、`钙钛矿学习xx平台`、`地热能在线`: 备注为公众号
- `ESPLAZA长时储能网`: 备注为公众号+网站，默认按备注跳过；如需抓取网站内容，可从备注中移除“公众号”
- `风电世界`: 链接为空

以下来源可以先由通用 RSS / 通用列表 scraper 尝试；如果日志出现 `TODO scraper needed`，需要人工补充列表页 CSS 选择器、文章页 HTML 样例或动态接口信息：

- `interesting engineering`
- `scitechdaily`
- `perovskite-info`
- `索比光伏`
- `4C Offshore`
- `全球风电网`
- `新能源网`
- `the information`
- `MIT Technology Review`
- `Informationsdienst Wissenschaft-idw`
