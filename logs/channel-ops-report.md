# 渠道运维总览

- 生成时间：2026-07-29T11:03:26.871157+08:00
- 渠道数：47
- 健康/正常空闲：12
- 异常渠道：22
- 待处理缺口：28

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | --- | --- |
| 4C Offshore | 2026-07-28 | zero | 1 | 0 | no target-date articles were collected | investigate |
| Electrek | 2026-07-28 | zero | 1 | 0 | no target-date articles were collected | investigate |
| electrive | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| ESS News | 2026-07-28 | zero | 1 | 0 | no target-date articles were collected | investigate |
| H2 View | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| interesting engineering | 2026-07-28 | zero | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| IT之家 | 2026-07-28 | zero | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| MIT Technology Review | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| perovskite-info | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-07-28 | zero | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine C&I PV | 2026-07-28 | zero | 1 | 3 | no target-date articles were collected | repair_then_reconfirm |
| Renewables Now | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| scitechdaily | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |
| Supply Chain Digital | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 中国核电信息网-国内 | 2026-07-28 | zero | 1 | 3 | no target-date articles were collected | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-07-28 | zero | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| 中国电力新闻网-科技 | 2026-07-28 | zero | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| 国际太阳能光伏网 | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 新华网科技 | 2026-07-28 | zero | 1 | 0 | no target-date articles were collected | investigate |
| 科学网新闻 | 2026-07-26 | zero | 2 | 2 | no target-date articles were collected | repair_then_reconfirm |
| 索比光伏 | 2026-07-28 | zero | 1 | 1 | no target-date articles were collected | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
