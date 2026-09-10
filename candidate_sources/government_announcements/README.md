# Government announcement candidates

这是一个默认关闭、等待人工审核的候选模块，没有注册到 `src/`、`SCRAPER_REGISTRY` 或 `sources.xlsx`。

当前可运行候选共 10 个：国家能源局“通知”“公告”、工信部“文件公示”，以及科技部、自然资源部、交通运输部、商务部、应急管理部、国家数据局、市场监管总局相关栏目。自然资源部暂为仅元数据，其余 9 个支持经严格路径和官网标识校验的机关文件纯文本。

发改委、农业农村部、生态环境部、水利部、财政部及工信部政策文件库因 robots 或页面合同不明确而保持 HOLD，具体原因见 [`COMPLIANCE.md`](COMPLIANCE.md)。

抓取只处理公开、同域的列表元数据和明确的机关文件正文纯文本；附件、图片、音视频、政策解读和站外链接不会下载。详细边界见 [`COMPLIANCE.md`](COMPLIANCE.md)。

从仓库根目录运行：

```powershell
python -m candidate_sources.government_announcements.probe
python -m candidate_sources.government_announcements.probe --catalog ministries
python -m candidate_sources.government_announcements.live_test
```

两个命令只向 `tmp/` 写证据/测试报告，不修改生产配置。
