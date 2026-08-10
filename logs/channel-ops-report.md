# 渠道运维总览

- 生成时间：2026-08-11T07:14:26.711639+08:00
- 渠道数：59
- 健康/正常空闲：33
- 异常渠道：12
- 待处理缺口：136

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-10 | zero | 0 | 0 | 0 | 1 | 6 | no target-date articles were collected | repair_then_confirm |
| Batteries News | 2026-08-10 | zero | 0 | 0 | 0 | 5 | 5 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-10 | healthy | 4199 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| Electrek | 2026-08-10 | healthy | 3656 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-10 | healthy | 3063 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-10 | healthy | 1508 | 0 | 0 | 0 | 5 | - | repair_then_confirm |
| H2 View | 2026-08-10 | degraded | 895 | 3 | 0 | 1 | 1 | 3 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-10 | healthy | 4133 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| INSIDEEVs | 2026-08-10 | degraded | 96 | 3 | 3 | 13 | 0 | 3 articles were not verified as full text | investigate |
| interesting engineering | 2026-08-10 | degraded | 3848 | 14 | 0 | 5 | 4 | 14 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-10 | healthy | 481 | 0 | 12 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-10 | healthy | 10339 | 0 | 0 | 0 | 5 | - | repair_then_reconfirm |
| NE时代 | 2026-08-10 | healthy | 3675 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| perovskite-info | 2026-08-10 | zero | 0 | 0 | 0 | 3 | 5 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-08-10 | healthy | 3266 | 0 | 0 | 0 | 6 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-10 | degraded | 901 | 1 | 1 | 1 | 6 | 1 articles were not verified as full text | repair_then_reconfirm |
| Renewables Now | 2026-08-10 | healthy | 420 | 0 | 19 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-10 | healthy | 5648 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-10 | healthy | 6334 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-10 | healthy | 701 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-10 | healthy | 696 | 0 | 6 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-10 | healthy | 650 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-10 | healthy | 787 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-10 | zero | 0 | 0 | 0 | 1 | 7 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-08-10 | zero | 0 | 0 | 0 | 13 | 13 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-10 | healthy | 358 | 0 | 20 | 0 | 4 | - | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-10 | healthy | 4936 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-10 | zero | 0 | 0 | 0 | 13 | 12 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-10 | zero | 0 | 0 | 0 | 13 | 11 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-08-10 | zero | 0 | 0 | 0 | 12 | 11 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-10 | healthy | 1130 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-10 | healthy | 414 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
