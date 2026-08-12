# 渠道运维总览

- 生成时间：2026-08-13T07:08:37.192508+08:00
- 渠道数：59
- 健康/正常空闲：30
- 异常渠道：15
- 待处理缺口：153

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-12 | zero | 0 | 0 | 0 | 3 | 8 | no target-date articles were collected | repair_then_confirm |
| Batteries News | 2026-08-12 | zero | 0 | 0 | 0 | 7 | 7 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-12 | healthy | 8193 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| Electrek | 2026-08-12 | healthy | 3533 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-12 | healthy | 3072 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-12 | zero | 0 | 0 | 0 | 1 | 6 | no target-date articles were collected | repair_then_confirm |
| H2 View | 2026-08-12 | degraded | 908 | 4 | 0 | 3 | 1 | 4 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-12 | zero | 0 | 0 | 0 | 1 | 3 | no target-date articles were collected | repair_then_reconfirm |
| INSIDEEVs | 2026-08-12 | degraded | 104 | 10 | 10 | 15 | 0 | 10 articles were not verified as full text | investigate |
| interesting engineering | 2026-08-12 | degraded | 3751 | 20 | 0 | 7 | 4 | 20 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-12 | healthy | 615 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-12 | healthy | 5735 | 0 | 0 | 0 | 5 | - | repair_then_reconfirm |
| NE时代 | 2026-08-12 | healthy | 3015 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| perovskite-info | 2026-08-12 | healthy | 3133 | 0 | 0 | 0 | 5 | - | repair_then_reconfirm |
| pv magazine | 2026-08-12 | healthy | 3237 | 0 | 0 | 0 | 6 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-12 | degraded | 2294 | 1 | 1 | 3 | 6 | 1 articles were not verified as full text | repair_then_reconfirm |
| Renewables Now | 2026-08-12 | healthy | 459 | 0 | 19 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-12 | healthy | 6497 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-12 | healthy | 3978 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-12 | healthy | 626 | 0 | 3 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-12 | healthy | 691 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-12 | healthy | 942 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-12 | healthy | 869 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-12 | zero | 0 | 0 | 0 | 3 | 9 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-08-12 | zero | 0 | 0 | 0 | 15 | 15 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-12 | healthy | 358 | 0 | 20 | 0 | 4 | - | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-12 | healthy | 1104 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-12 | zero | 0 | 0 | 0 | 15 | 14 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-12 | zero | 0 | 0 | 0 | 15 | 13 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-08-12 | zero | 0 | 0 | 0 | 14 | 13 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-12 | degraded | 859 | 1 | 1 | 1 | 2 | 1 articles were not verified as full text | repair_then_reconfirm |
| 索比光伏 | 2026-08-12 | zero | 0 | 0 | 0 | 1 | 3 | no target-date articles were collected | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
