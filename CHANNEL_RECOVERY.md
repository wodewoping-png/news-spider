# 渠道异常自反馈与自动补抓

> 日常维护已统一到 [`CHANNEL_OPERATIONS.md`](CHANNEL_OPERATIONS.md) 和
> `python -m src.channel_ops`。本文件保留底层恢复模块说明和兼容命令。

每日抓取结束后，`src.audit` 会把日更渠道的零产出或抓取失败按“渠道 + 缺失日期”写入
`logs/recovery-queue.json`。同一缺口重复审查不会重复建单。

## 状态流转

`pending_confirmation` → `confirmed` → `recovering` → `recovered`

- `pending_confirmation`：已告警，等待人工判断和修复。
- `confirmed`：人工确认修复完成，可以补抓。
- `recovering`：补抓执行中。
- `recovered`：原日期已抓到文章，缺口自动关闭。
- `recovery_failed`：修复后补抓仍失败，记录最新错误，需再次修复和确认。
- `ignored`：人工确认当天确实没有更新或不需要补抓。

异常原因会结合任务错误、候选文章数和正文访问数给出，例如 HTTP 403/404/429、
请求超时、TLS/DNS/robots 问题、没有候选、候选被日期或去重逻辑全部过滤、发布日期
或正文解析异常。底层原始错误保存在 `technical_reason`。

## 人工处理

查看待办：

```bash
python -m src.recovery list --status pending_confirmation
```

修复 scraper、RSS 地址或渠道配置并验证后，确认该渠道的所有历史缺口：

```bash
python -m src.recovery confirm \
  --source "渠道名称" \
  --note "已修复列表选择器并验证发布日期"
```

只确认指定日期：

```bash
python -m src.recovery confirm \
  --source "渠道名称" \
  --date 2026-07-22 \
  --note "已修复"
```

如果人工确认当天确实没有内容：

```bash
python -m src.recovery ignore \
  --source "渠道名称" \
  --date 2026-07-22 \
  --note "官网当天没有发布"
```

立即执行已确认任务：

```bash
python -m src.recovery run --sources sources.xlsx
```

也可以在 GitHub Actions 中运行 **Channel Recovery**，填写准确渠道名称、处理动作和人工备注。
日常任务会在新一轮抓取前自动消费所有 `confirmed` 条目。

## 告警与补抓规则

- 每日工作流最后执行 `python -m src.recovery check`；存在未确认或补抓失败条目时，
  会输出 GitHub Actions error annotation 并使任务标红，数据和日志会先正常提交。
- 配置钉钉机器人后，首次异常、补抓失败和补抓成功会主动推送到群聊；相同状态不会重复通知。
- 补抓只运行对应渠道和原缺失日期，不重跑其他渠道。
- 补抓使用更大的候选窗口（默认检查 500 条、最多保留 100 篇），提高找回旧日期文章的概率。
- URL 仍使用全局去重；重复执行不会重复写文章。
- 补抓成功后，下次审查会把历史统计行更新为 `recovered`，并写回真实文章数。
- `recovery_failed` 不会无限自动重试；需要人工再次修复并执行 `confirm`，避免故障请求失控。
