# 行业图景语义分类

抓取程序可以调用智谱 Z.AI 的语言模型，根据 `configs/industry_taxonomy.json` 中的行业语义定义判断新闻所属领域。分类表来自 `行业图景.xmind`，覆盖：

- 零碳产业
- AI 与智能科技
- 通用技术

程序理解新闻标题与正文的核心事件后进行多标签分类，不做简单关键词计数。一篇新闻最多匹配三个末级领域；没有足够证据时标记为“未分类”。模型返回的路径必须通过本地分类表白名单校验，无法写入不存在的领域。

## 配置 Z.AI

在本地 PowerShell 中临时设置 API 密钥：

```powershell
$env:ZAI_API_KEY = "你的 Z.AI API Key"
$env:ZAI_MODEL = "glm-5.2"
```

密钥仅从环境变量读取，不要写入源码或配置文件。默认接口为：

```text
https://open.bigmodel.cn/api/paas/v4/chat/completions
```

如账号使用其它兼容入口，可通过 `ZAI_API_URL` 覆盖。普通开放平台密钥继续使用上述 OpenAI 兼容接口；如使用 Anthropic/Coding Plan 兼容入口，可将 `ZAI_API_URL` 设置为 `https://open.bigmodel.cn/api/anthropic`，程序会自动改用 Anthropic Messages 协议（`/v1/messages`、`x-api-key` 和对应响应格式），不要把该地址当作 OpenAI 请求 URL 直接替换。默认模型 `glm-5.2`，也可通过 `ZAI_MODEL` 或命令行参数切换。分类请求会关闭深度思考，以获得更低延迟和更稳定的 JSON 判断。

GitHub Actions 中需要添加：

- Repository secret：`ZAI_API_KEY`
- Repository variable（可选）：`ZAI_MODEL`
- Repository variable（可选）：`ZAI_API_URL`

`.github/workflows/daily-news.yml` 已将这些值传给每日抓取任务。Actions 默认使用 `https://open.bigmodel.cn/api/anthropic` 以适配 Coding Plan；如 Secrets 中是普通开放平台密钥，请把 `ZAI_API_URL` 仓库变量设为 `https://open.bigmodel.cn/api/paas/v4/chat/completions`。未配置密钥时，抓取照常运行，只跳过分类。额度、鉴权或请求配置错误会立即停止本轮后续分类请求，避免对每个渠道重复重试，但不影响新闻采集。

## 每日抓取自动分类

原有命令无需变化：

```powershell
python -m src.channel_ops cycle --sources sources.xlsx
```

配置 `ZAI_API_KEY` 后，新抓取或正文刷新的文章会在写入 JSONL 前自动分类。若 Z.AI 请求失败，抓取不会中止，文章会以 `industry_classification_status=error` 保存，稍后可补跑。

如需临时禁止 API 调用：

```powershell
python -m src.main --skip-industry-classification
```

## 给已有新闻补分类

分类所有尚未使用当前分类表处理的文章：

```powershell
python -m src.industry_classifier --input data/articles.jsonl
```

只处理某个发布日期，并刷新当天 CSV：

```powershell
python -m src.industry_classifier `
  --input data/articles.jsonl `
  --target-date 2026-08-12 `
  --csv data/articles-2026-08-13.csv
```

常用参数：

- `--limit 20`：仅处理前 20 篇待分类文章，用于小规模验证。
- `--force`：即使分类表版本未变化，也强制重新分类。
- `--batch-size 6`：调整每次 API 请求包含的文章数。
- `--max-content-chars 12000`：调整每篇新闻发送给模型的最大正文字符数。
- `--min-confidence 0.65`：低于阈值的匹配不保存。
- `--model glm-5.2`：切换智谱模型。

## 输出字段

JSONL 与 CSV 会增加：

- `industry_primary_path`：最高置信度完整路径，例如 `零碳产业 > 能量循环 > 能量存储 > 电化学储能 > 二次电池 > 锂电池`。
- `industry_top_level`：一级行业。
- `industry_leaf`：末级领域。
- `industry_classifications`：最多三个匹配，包含完整路径、置信度和模型给出的简短依据。
- `industry_classification_status`：`classified`、`unclassified` 或 `error`。
- `industry_classified_at`：分类时间。
- `industry_classifier_model`：使用的模型。
- `industry_taxonomy_version`：分类表版本。
- `industry_classification_error`：失败批次的脱敏错误摘要，成功分类时为空。

## 调整领域定义

领域及对应语义说明保存在 `configs/industry_taxonomy.json`。修改定义后应同步提高 `version`，这样补分类命令会自动识别旧版本结果并重新处理。不要删除 `path` 层级或使用分类表外路径；程序会拒绝重复路径和无语义说明的条目。
