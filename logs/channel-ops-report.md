# 渠道运维总览

- 生成时间：2026-08-26T07:14:22.451275+08:00
- 渠道数：59
- 健康/正常空闲：38
- 异常渠道：7
- 待处理缺口：241

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-25 | healthy | 1062 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-08-25 | zero | 0 | 0 | 0 | 1 | 18 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-25 | healthy | 6451 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-25 | healthy | 4952 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-08-25 | healthy | 3264 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-25 | healthy | 1515 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-08-25 | degraded | 849 | 3 | 0 | 2 | 1 | 3 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-25 | zero | 0 | 0 | 0 | 2 | 7 | no target-date articles were collected | repair_then_reconfirm |
| interesting engineering | 2026-08-25 | healthy | 3747 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| IT之家 | 2026-08-25 | healthy | 600 | 0 | 8 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-25 | idle | 0 | 0 | 0 | 0 | 8 | all observed candidates were published outside the target date (2026-08-26) | repair_then_reconfirm |
| NE时代 | 2026-08-25 | idle | 0 | 0 | 0 | 0 | 7 | all observed candidates were published outside the target date (2026-08-21 to 2026-08-24) | repair_then_confirm |
| perovskite-info | 2026-08-25 | idle | 0 | 0 | 0 | 0 | 7 | all observed candidates were published outside the target date (2026-08-16 to 2026-08-24) | repair_then_reconfirm |
| pv magazine | 2026-08-25 | healthy | 3512 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-25 | degraded | 2951 | 1 | 1 | 1 | 6 | 1 articles were not verified as full text | repair_then_reconfirm |
| Renewables Now | 2026-08-25 | healthy | 497 | 0 | 17 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-25 | healthy | 6389 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-25 | healthy | 4589 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-25 | healthy | 432 | 0 | 4 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-25 | healthy | 756 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-25 | healthy | 1352 | 0 | 1 | 0 | 3 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-25 | zero | 0 | 0 | 0 | 1 | 5 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-08-25 | healthy | 752 | 0 | 4 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-25 | idle | 0 | 0 | 0 | 0 | 26 | all observed candidates were published outside the target date (2026-08-07 to 2026-08-24) | repair_then_confirm |
| 北极星储能网 | 2026-08-25 | zero | 0 | 0 | 0 | 2 | 17 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-25 | healthy | 1621 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-25 | zero | 0 | 0 | 0 | 2 | 26 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-25 | healthy | 1060 | 0 | 1 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-25 | idle | 0 | 0 | 0 | 0 | 23 | all observed candidates were published outside the target date (2026-07-03 to 2026-08-18) | repair_then_confirm |
| 科学网新闻 | 2026-08-25 | healthy | 904 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-25 | healthy | 750 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
