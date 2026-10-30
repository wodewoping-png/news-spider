# 政策语义分类

`configs/policy_taxonomy.json` 单独保存政策五级分类，共 65 个可选节点。路径仅包含有效层级，展示或导出时用 `NA` 补足第 1 至第 5 级。模型先判断新闻是否包含实质政策、规划、监管措施或具名政策解读，再按作用机制选择有正文依据的最深节点；无法进一步细分时可以选择上级。最多保存三个不同的政策工具，结果必须通过本地路径白名单校验。

一般新闻抓取每日先运行政策分类，再对非政策新闻运行原行业分类。`data/articles.jsonl` 和每日 CSV 新增 `policy_primary_path`、`policy_level_1` 至 `policy_level_5`、`policy_classifications`、`policy_classification_status` 等字段。状态 `classified` 表示匹配政策，`non_policy` 表示不是政策，`error` 表示模型调用失败；无密钥时跳过一般新闻分类。

部委公告归档在生成 `国内政策清单.csv` 前对政策公告分类，写入“政策分类路径”“政策第1级”至“政策第5级”“政策分类状态”“政策分类依据”“政策分类明细”；同样保存到每条公告的 `公告.json` 和当日 `索引.json`。国家统计局统计数据和矿山安全事故通报的独立清单不进入政策分类。每周一构建的 `国内政策周汇总.xlsx` 在“政策汇总”工作表继承当日清单中的分类列，历史日报和周报不会自动重写。

两套分类使用同一个 `ZAI_API_KEY`、`ZAI_MODEL` 和 `ZAI_API_URL` 环境配置。部委归档工作流也传入这些变量。无密钥时公告的分类状态为 `not_configured`，归档仍正常完成。需要跳过公告分类时使用 `python -m src.government_archive --skip-policy-classification`；跳过每日新闻两套 AI 分类时使用 `python -m src.main --skip-industry-classification`。
