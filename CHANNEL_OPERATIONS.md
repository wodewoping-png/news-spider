# 渠道运维管理系统

`src.channel_ops` 是抓取渠道的统一运维入口。它复用现有抓取、审计、恢复和钉钉模块，
但集中管理运行顺序、状态归并和操作入口。

## 每日闭环

```text
已确认缺口补抓
      ↓
运行所有渠道（单渠道失败隔离）
      ↓
生成每日质量审计与缺口工单
      ↓
归并渠道当前状态 + 追加运行事件
      ↓
钉钉仅推送新的状态变化
```

系统不会因为一个网站超时、拒绝访问或解析失败而停止其他渠道。异常记录包含渠道、目标
日期、发生时间、错误类型、错误原因、抓取模式、候选数、正文访问数和实际产出数。
如果某次 Action 整体延迟、取消或失败，导致一个应运行日期完全没有渠道记录，下一次成功
周期会在最近 31 天范围内自动发现这些日历缺口；该渠道当天已经存在历史文章时不重复
建单，只为确实缺少数据的渠道建立恢复工单。

## 统一运行

本地或 GitHub Actions 的正常日常入口：

```bash
python -m src.channel_ops cycle --sources sources.xlsx
```

补抓指定日期：

```bash
python -m src.channel_ops cycle \
  --sources sources.xlsx \
  --target-date 2026-07-28
```

`cycle` 依次执行：

1. 消费已经人工确认修复的历史缺口；
2. 运行每日抓取和质量审计；
3. 更新统一运维台账和报告；
4. 自动确认并补抓“整日运行缺失”产生的数据缺口；
5. 推送新的钉钉状态变化。

钉钉未配置或推送失败不会影响抓取数据落盘。
整日运行缺失默认自动补抓；临时排查时可使用 `--no-auto-backfill` 禁用。网站本身的超时、
认证或解析异常不会自动确认，仍需修复后再进入验证，防止无效无限重试。

## 运维台账

| 文件 | 用途 |
| --- | --- |
| `logs/channel-operations.jsonl` | 不可变的逐次抓取事件，便于追溯某渠道何时、为何失败 |
| `logs/channel-operations.csv` | 每个渠道当前状态，适合筛选和人工检查 |
| `logs/channel-ops-state.json` | 幂等状态、最近成功时间和连续异常次数 |
| `logs/channel-ops-report.json` | 供自动化读取的当前总览 |
| `logs/channel-ops-report.md` | GitHub Actions 中展示的中文运维总览 |
| `logs/channel-daily-stats.csv` | 渠道×日期的产量、质量和异常基线 |
| `logs/recovery-queue.json` | 渠道×缺失日期的修复/补抓状态机 |
| `logs/source-errors.jsonl` | 抓取程序记录的底层渠道异常 |

查看当前状态：

```bash
python -m src.channel_ops status
```

手工重新归并最近一次健康报告：

```bash
python -m src.channel_ops reconcile
```

同一份健康报告可以安全重复归并，不会重复追加事件或累计连续异常次数。

## 状态和下一步动作

抓取状态：

- `healthy`：有产出且正文质量达标；
- `already_collected`：目标日期已有文章，重复运行没有新增；
- `idle`：按周刊/月刊/工作日等周期判断，当天不要求产出；
- `degraded`：有文章，但存在正文过短等质量问题；
- `zero`：该渠道当天应有产出但抓取为零；
- `failed`：请求、认证、解析或程序异常；
- `skipped`：来源配置明确要求跳过。
- `recovered`：对应缺失日期已经补抓到文章；
- `verified_no_news`：人工确认该日期确实无新闻，不计为缺口。

运维动作：

- `investigate`：异常已发现，等待诊断；
- `repair_then_confirm`：已形成缺口工单，修复后需确认；
- `automatic_backfill`：修复已确认，等待或正在补抓；
- `repair_then_reconfirm`：补抓验证失败，需要继续修复并重新确认；
- `none`：当前无待处理动作。

## 修复、验证和补缺

修复 scraper、RSS 或渠道配置后，确认并立即验证所有该渠道缺口：

```bash
python -m src.channel_ops resolve confirm \
  --source "渠道名称" \
  --note "已修复并验证列表和发布日期解析" \
  --sources sources.xlsx \
  --run \
  --notify
```

只处理指定日期，可重复使用 `--date`：

```bash
python -m src.channel_ops resolve confirm \
  --source "渠道名称" \
  --date 2026-07-28 \
  --note "已修复" \
  --run \
  --notify
```

如果确认当天确实没有新闻：

```bash
python -m src.channel_ops resolve ignore \
  --source "渠道名称" \
  --date 2026-07-28 \
  --note "官网当天无新闻" \
  --notify
```

补抓只运行对应渠道和缺失日期。找到文章后自动标记 `recovered` 并发送恢复通知；仍为空或
再次报错则标记 `recovery_failed`，不会无限重试。

GitHub Actions 的 **Channel Recovery** 提供相同操作，不需要在命令行执行。

## 告警策略

钉钉推送以下状态变化：

- 首次进入 `pending_confirmation`；
- 修复验证后进入 `recovery_failed`；
- 成功补齐后进入 `recovered`。

相同缺口的相同状态只发送一次。GitHub Actions 末尾还会输出所有
`pending_confirmation` 和 `recovery_failed` 条目的 warning annotation，便于在没有
钉钉时仍能发现问题。

## 密钥安全

Webhook、机器人密钥和认证 RSS 凭据只能保存在 GitHub Actions Secrets。运维台账会对
常见的 token、password、secret、authorization 字段进行脱敏，禁止把真实凭据写入
源码、Excel、日志、Issue 或命令参数。
