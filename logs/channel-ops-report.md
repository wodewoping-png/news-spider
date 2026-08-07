# 渠道运维总览

- 生成时间：2026-08-07T10:06:42.651416+08:00
- 渠道数：59
- 健康/正常空闲：33
- 异常渠道：12
- 待处理缺口：98

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-06 | zero | 0 | 0 | 0 | 4 | 4 | no target-date articles were collected | repair_then_confirm |
| Batteries News | 2026-08-06 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| Electrek | 2026-08-06 | healthy | 3978 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-06 | zero | 0 | 0 | 0 | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-06 | healthy | 1386 | 0 | 0 | 0 | 5 | - | repair_then_confirm |
| H2 View | 2026-08-06 | degraded | 725 | 6 | 0 | 4 | 1 | 6 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-06 | healthy | 5871 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| INSIDEEVs | 2026-08-06 | degraded | 119 | 11 | 11 | 9 | 0 | 11 articles were not verified as full text | investigate |
| interesting engineering | 2026-08-06 | degraded | 3679 | 20 | 0 | 1 | 4 | 20 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-06 | healthy | 764 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-06 | healthy | 6752 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| NE时代 | 2026-08-06 | healthy | 3185 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| perovskite-info | 2026-08-06 | healthy | 2048 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| pv magazine | 2026-08-06 | healthy | 3231 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-06 | healthy | 3972 | 0 | 0 | 0 | 6 | - | repair_then_reconfirm |
| Renewables Now | 2026-08-06 | healthy | 571 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-06 | healthy | 6157 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-06 | healthy | 6400 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-06 | healthy | 562 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-06 | healthy | 676 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-06 | healthy | 1184 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-06 | healthy | 1043 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-06 | zero | 0 | 0 | 0 | 4 | 5 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-08-06 | zero | 0 | 0 | 0 | 9 | 9 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-06 | healthy | 358 | 0 | 20 | 0 | 2 | - | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-06 | healthy | 1672 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-06 | zero | 0 | 0 | 0 | 9 | 8 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-06 | zero | 0 | 0 | 0 | 9 | 7 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-08-06 | zero | 0 | 0 | 0 | 8 | 7 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-06 | degraded | 1065 | 1 | 1 | 1 | 2 | 1 articles were not verified as full text | repair_then_reconfirm |
| 索比光伏 | 2026-08-06 | healthy | 1537 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
