# 渠道运维总览

- 生成时间：2026-08-27T11:53:41.527010+08:00
- 渠道数：59
- 健康/正常空闲：39
- 异常渠道：6
- 待处理缺口：247

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-26 | healthy | 1250 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-08-26 | idle | 0 | 0 | 0 | 0 | 18 | all observed candidates were published outside the target date (2026-08-08 to 2026-08-25) | repair_then_confirm |
| Data Center Knowledge | 2026-08-26 | healthy | 8692 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-26 | healthy | 5089 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-08-26 | healthy | 2536 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-26 | healthy | 1222 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-08-26 | degraded | 836 | 5 | 0 | 3 | 2 | 5 articles were not verified as full text (paywall_or_login_wall) | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-26 | healthy | 8790 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| interesting engineering | 2026-08-26 | healthy | 3683 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| IT之家 | 2026-08-26 | idle | 0 | 0 | 0 | 0 | 2 | all observed candidates were published outside the target date (2026-08-27) | repair_then_reconfirm |
| MIT Technology Review | 2026-08-26 | healthy | 9573 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| NE时代 | 2026-08-26 | idle | 0 | 0 | 0 | 0 | 7 | all observed candidates were published outside the target date (2026-08-24 to 2026-08-27) | repair_then_confirm |
| perovskite-info | 2026-08-26 | healthy | 3790 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine | 2026-08-26 | healthy | 3212 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-26 | degraded | 2711 | 1 | 1 | 2 | 7 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-08-26 | healthy | 1557 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-26 | healthy | 6622 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-26 | healthy | 6687 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-26 | healthy | 627 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-26 | healthy | 869 | 0 | 1 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-26 | healthy | 792 | 0 | 1 | 0 | 3 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-26 | healthy | 1016 | 0 | 0 | 0 | 5 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-26 | healthy | 819 | 0 | 3 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-26 | zero | 0 | 0 | 0 | 1 | 27 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-26 | zero | 0 | 0 | 0 | 3 | 18 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-26 | healthy | 1048 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-26 | zero | 0 | 0 | 0 | 3 | 27 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-26 | healthy | 999 | 0 | 1 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-26 | zero | 0 | 0 | 0 | 1 | 24 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-26 | healthy | 1019 | 0 | 1 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-26 | healthy | 383 | 0 | 4 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
