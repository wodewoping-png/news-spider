# 学术前沿与会议追踪

- `mtl.inew.cn—学术前沿` 已列入 `sources.xlsx`，跟随现有每日新闻任务，限定学术前沿栏目链接。该站在开发环境中连接超时，详情链接结构和正文提取尚未完成真实站点验证；运行时访问失败会进入现有渠道健康记录，不能将零篇当作成功抓取。
- `mtl.inew.cn—学术会议` 和 `北京国际科技创新中心—会议日历` 使用独立月度任务 `.github/workflows/conference-monthly.yml`，每月 1 日北京时间 09:00 扫描本月和下月，结果在 `data/conferences/YYYY-MM/会议清单.csv`，每个来源的状态在 `索引.json`。会议日期与新闻发布日期分开处理。
- NCSTI 使用科技动态页加载的公开日历接口：`/kw/meeting/cale` 获取会议日期，`/kw/meeting/query` 获取会议详情；只收 `ChannelId=79` 的“会议”。已实测该接口可返回会议标题、日期、地点和详情 URL。`mtl.inew.cn` 的会议页当前无法连接，月度运行会将其标为 `failed`，不生成臆测会议。

手动重跑一个月份：

```bash
python -m src.conference_monthly --month 2026-11 --output-dir data/conferences
```

任务遇到单个来源失败仍写出可用的会议清单和来源状态，最后返回失败状态以提示补抓。访问权限恢复后，应以真实页面校验 `mtl.inew.cn` 的链接、日期和详情结构，再将该来源状态视为已完成接入。
