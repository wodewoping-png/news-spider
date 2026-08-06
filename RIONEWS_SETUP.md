# RIOnews 接入说明

以下渠道已停止直接访问网页，改为导入 RIOnews 每日 Excel 中对应的发布媒体前缀：

- `中国能源网`：`中国能源网_`（新能源、节能低碳）
- `电池网`：`电池网_`（国内、企业等新闻栏目）
- `我爱电车网`：`我爱电车网_`
- `国际能源网`：`国际能源网_`

导入后的文章仍使用 `sources.xlsx` 中各自的渠道名称作为 `source_name`，沿用原有
主干领域和细分领域，并继续使用全局 URL 去重。

## 本地运行

将 `RIONEWS_DAILY_DIR` 指向 RIOnews 的 `daily` 目录：

```powershell
$env:RIONEWS_DAILY_DIR='D:\GitHub\wechat-article-intel-automation-main\RIOnews\daily'
python -m src.main --sources sources.xlsx `
  --only-source "中国能源网" `
  --only-source "电池网" `
  --only-source "我爱电车网" `
  --only-source "国际能源网" `
  --target-date 2026-08-04 --skip-audit
```

本地已有每日 Excel 时不会调用 API。

## GitHub Actions

每日工作流会先调用 `python -m src.rionews_fetch`，把 API 导出的 Excel 拆到
Runner 临时目录，再运行统一抓取任务。因此不需要每天手工上传 Excel，大文件和
API 凭据也不会进入仓库。

在仓库 `Settings → Secrets and variables → Actions` 中配置：

Secrets：

- `RIO_USERNAME`
- `RIO_PASSWORD`

Variables（可选）：

- `RIO_BASE_URL`：默认 `http://api.surbot.cn/data`
- `RIO_SYSTEM_TYPE`：默认 `CATL-RIO`
- `RIO_DAYS`：默认 `7`

如果未配置 Secrets，工作流会继续抓取其他渠道，但上述 RIOnews 渠道会记录为没有
可用的每日文件。不要把现有 `RIOnews/config.json` 的账号或密码复制进仓库。
