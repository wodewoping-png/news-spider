# 渠道运维总览

- 生成时间：2026-09-05T08:27:39.102985+08:00
- 渠道数：59
- 健康/正常空闲：35
- 异常渠道：10
- 待处理缺口：306

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-04 | healthy | 1222 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-04 | zero | 0 | 0 | 0 | 1 | 22 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-09-04 | healthy | 6299 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-04 | healthy | 4222 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-04 | healthy | 2672 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-04 | healthy | 1453 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-04 | zero | 0 | 0 | 0 | 5 | 9 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-04 | healthy | 4335 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| interesting engineering | 2026-09-04 | healthy | 3696 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-04 | healthy | 566 | 0 | 9 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-04 | healthy | 8117 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| NE时代 | 2026-09-04 | healthy | 3330 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-04 | zero | 0 | 0 | 0 | 1 | 11 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-09-04 | healthy | 4814 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-04 | healthy | 3900 | 0 | 0 | 0 | 11 | - | repair_then_reconfirm |
| Renewables Now | 2026-09-04 | healthy | 1078 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-09-04 | healthy | 5546 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-04 | healthy | 4314 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| the information | 2026-09-04 | failed | 0 | 0 | 0 | 1 | 1 | Required fetch failed: https://www.theinformation.com/subscriber_feed (HTTP 403) | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-04 | healthy | 610 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-04 | healthy | 652 | 0 | 7 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-04 | zero | 0 | 0 | 0 | 1 | 6 | no target-date articles were collected | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-04 | zero | 0 | 0 | 0 | 5 | 10 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-04 | zero | 0 | 0 | 0 | 3 | 16 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-09-04 | zero | 0 | 0 | 0 | 3 | 31 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-09-04 | zero | 0 | 0 | 0 | 5 | 25 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-04 | healthy | 1467 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-04 | zero | 0 | 0 | 0 | 12 | 36 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-09-04 | healthy | 646 | 0 | 1 | 0 | 20 | - | repair_then_confirm |
| 电池网 | 2026-09-04 | idle | 0 | 0 | 0 | 0 | 25 | all observed candidates were published outside the target date (2026-07-20 to 2026-08-30) | repair_then_confirm |
| 科学网新闻 | 2026-09-04 | idle | 0 | 0 | 0 | 0 | 4 | all observed candidates were published outside the target date (2026-09-05) | repair_then_reconfirm |
| 索比光伏 | 2026-09-04 | healthy | 654 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
