# 钉钉群告警配置

代码已经包含钉钉群机器人 Webhook、加签、关键词匹配、状态去重和 GitHub Actions 对接。
凭据不会写入仓库；配置缺失时，工作流会安全跳过钉钉推送。

## 1. 创建群机器人

在需要接收告警的钉钉群中进入机器人管理，创建群机器人并复制 Webhook。

安全设置建议选择“加签”，保存 `SEC` 开头的密钥。同时可以配置自定义关键词：

```text
渠道抓取告警
```

代码默认使用同一个关键词，并保证关键词同时出现在消息标题和正文中。如果机器人配置了其他
关键词，需要在 GitHub 中添加同名变量 `DINGTALK_KEYWORD`。

## 2. 配置 GitHub

进入仓库：

```text
Settings → Secrets and variables → Actions
```

在 **Secrets** 中添加：

| 名称 | 内容 | 必需 |
|---|---|---|
| `DINGTALK_WEBHOOK` | 完整机器人 Webhook，包含 access_token | 是 |
| `DINGTALK_SECRET` | `SEC` 开头的加签密钥 | 使用加签时必需 |

如果机器人关键词不是默认的“渠道抓取告警”，在 **Variables** 中添加：

| 名称 | 内容 |
|---|---|
| `DINGTALK_KEYWORD` | 机器人安全设置里的自定义关键词 |

不要把 Webhook、access_token 或 `SEC` 密钥提交到代码、配置文件或 Issue。

## 3. 验证

配置完成后，先在 Actions 页面手动运行 **DingTalk Alert Test**。群内收到
“渠道抓取告警：连接测试”即表示 Webhook、加签和关键词都匹配成功。

正式运行时，恢复队列出现以下状态变化会推送：

- 首次出现 `pending_confirmation`；
- 补抓变为 `recovery_failed`；
- 补抓成功变为 `recovered`。

相同状态只推送一次。发送成功后的状态保存在
`logs/notification-state.json`，会随其他日志一起提交。

消息包含渠道、缺失日期、异常原因、处理状态和当前 GitHub Actions 运行链接。

本地测试时可临时设置环境变量，但不要保存到项目文件：

```powershell
$env:DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=..."
$env:DINGTALK_SECRET = "SEC..."
$env:DINGTALK_KEYWORD = "渠道抓取告警"
python -m src.channel_ops notify
```

## 4. 故障兜底

钉钉发送失败不会阻断爬虫、数据提交或历史补抓。GitHub Actions 原生红色告警仍会保留，
推送失败也会显示在工作流日志中，并在下一次运行时重试未成功记录的状态变化。
