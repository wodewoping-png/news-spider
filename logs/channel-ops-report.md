# 渠道运维总览

- 生成时间：2026-08-09T06:47:13.744347+08:00
- 渠道数：59
- 健康/正常空闲：33
- 异常渠道：12
- 待处理缺口：116

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 5 | no target-date articles were expected for this source schedule | repair_then_confirm |
| Batteries News | 2026-08-08 | zero | 0 | 0 | 0 | 3 | 3 | no target-date articles were collected | repair_then_confirm |
| Electrek | 2026-08-08 | healthy | 4216 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 2 | no target-date articles were expected for this source schedule | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 5 | no target-date articles were expected for this source schedule | repair_then_confirm |
| H2 View | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 1 | no target-date articles were expected for this source schedule | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 2 | no target-date articles were expected for this source schedule | repair_then_reconfirm |
| INSIDEEVs | 2026-08-08 | degraded | 135 | 3 | 3 | 11 | 0 | 3 articles were not verified as full text | investigate |
| interesting engineering | 2026-08-08 | degraded | 3770 | 13 | 0 | 3 | 4 | 13 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-08 | healthy | 497 | 0 | 10 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-08 | zero | 0 | 0 | 0 | 1 | 4 | no target-date articles were collected | repair_then_reconfirm |
| NE时代 | 2026-08-08 | zero | 0 | 0 | 0 | 1 | 3 | no target-date articles were collected | repair_then_confirm |
| perovskite-info | 2026-08-08 | zero | 0 | 0 | 0 | 1 | 3 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-08-08 | zero | 0 | 0 | 0 | 1 | 5 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 6 | no target-date articles were expected for this source schedule | repair_then_reconfirm |
| Renewables Now | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 1 | no target-date articles were expected for this source schedule | repair_then_reconfirm |
| scitechdaily | 2026-08-08 | healthy | 6623 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-08 | healthy | 3470 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-08 | healthy | 640 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-08 | healthy | 630 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 2 | no target-date articles were expected for this source schedule | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 4 | no target-date articles were expected for this source schedule | repair_then_reconfirm |
| 中国能源网 | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 6 | no target-date articles were expected for this source schedule | repair_then_confirm |
| 光伏测试网 | 2026-08-08 | zero | 0 | 0 | 0 | 11 | 11 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-08 | zero | 0 | 0 | 0 | 1 | 3 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 3 | no target-date articles were expected for this source schedule | repair_then_confirm |
| 国际能源网 | 2026-08-08 | zero | 0 | 0 | 0 | 11 | 10 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-08 | zero | 0 | 0 | 0 | 11 | 9 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-08-08 | zero | 0 | 0 | 0 | 10 | 9 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-08 | healthy | 1188 | 0 | 1 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-08 | idle | 0 | 0 | 0 | 0 | 2 | no target-date articles were expected for this source schedule | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
