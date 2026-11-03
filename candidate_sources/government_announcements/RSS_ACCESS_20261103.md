# 受限部委的官网 RSS 核查（2026-11-03）

核查对象是此前待核准或暂缓的 20 个机构，原始清单见 [替代访问记录](ALTERNATIVE_ACCESS_20261022.md)。仅把官网明确公布、且在 GitHub Actions 环境能通过 robots 检查、返回有效 RSS/Atom 和可用发布日期的栏目视为可接入。第三方 RSSHub 路由会继续抓原站，不能代替官网许可。诊断程序只读 RSS XML，不下载条目详情，也不会自动改变生产渠道状态。

| 机构及栏目 | 官网线索 | GitHub Actions 实测 | 决定 |
|---|---|---|---|
| 国家发展改革委政策/解读 | 官网[政务公开](https://www.ndrc.gov.cn/xxgk/)列出政策和解读，[公开指南](https://zfxxgk.ndrc.gov.cn/wap/gkzn.jsp)列出网站与新媒体，没有找到该两栏的官方 RSS 地址 | 无可核准的官方 RSS URL；原站 robots 403 的障碍仍在 | 继续暂缓，不使用第三方代抓取 RSS |
| 人社部政策法规、政策解读 | [官网 RSS 订阅中心](https://www.mohrss.gov.cn/SYrlzyhshbzb/zxhd/RSS/xxdy/)公布了两个 HTTP XML 地址 | HTTP 和同路径 HTTPS 的 `robots.txt` 都返回 HTML，而非有效 robots 文件；按现有严格策略停止在 RSS 请求之前 | 保留待核准，不能把官网网页列出地址等同于可用订阅 |
| 国家国防科工局政策法规 | [官网 RSS 入口](https://www.sastind.gov.cn/n10118180/index.html)链接到 XML | XML 返回 50 个条目；示例缺完整发布日期，链接为相对路径。现有网站详情页已有发布日期核验 | 不单独增加重复渠道；既有栏目继续采用详情页日期 |
| 其余待核准/暂缓机构 | 未找到能够逐站核准的官网政策 RSS 地址 | 无明确端点就不猜测 `/rss.xml` 或接入第三方聚合 | 保持原状态，逐站继续寻找官方端点 |

实测记录：[PR #49 的 Central policy channel contracts 工作流](https://github.com/wodewoping-png/news-spider/actions/runs/41628619098)。统计局官网也公布了[最新发布和数据解读 RSS](https://www.stats.gov.cn/wzgl/rss/)，但两份 XML 在诊断的 2 MB 上限内没有读完，不能用该对照判断它们不可用；统计局栏目已有独立抓取配置。

若后续出现发改委等机构的官网 RSS 地址，应先确认同源 robots、返回的 XML 格式、条目原始发布日期、文章链接主机、栏目覆盖和与既有渠道的去重，再加入日更。只有标题而无日期的订阅不能直接写入按日政策清单。
