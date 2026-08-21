# 渠道运维总览

- 生成时间：2026-08-22T07:13:33.448601+08:00
- 渠道数：59
- 健康/正常空闲：35
- 异常渠道：10
- 待处理缺口：223

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-21 | healthy | 1205 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-08-21 | zero | 0 | 0 | 0 | 18 | 16 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-21 | healthy | 7948 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-21 | healthy | 4379 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-21 | healthy | 3425 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-21 | zero | 0 | 0 | 0 | 1 | 8 | no target-date articles were collected | repair_then_confirm |
| H2 View | 2026-08-21 | degraded | 1701 | 2 | 0 | 5 | 1 | 2 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-21 | healthy | 7368 | 0 | 0 | 0 | 5 | - | repair_then_reconfirm |
| interesting engineering | 2026-08-21 | degraded | 3613 | 1 | 0 | 2 | 4 | 1 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-21 | healthy | 677 | 0 | 7 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-21 | healthy | 7048 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| NE时代 | 2026-08-21 | healthy | 2751 | 0 | 0 | 0 | 6 | - | repair_then_confirm |
| perovskite-info | 2026-08-21 | healthy | 3780 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine | 2026-08-21 | healthy | 3601 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-21 | degraded | 4007 | 1 | 1 | 5 | 6 | 1 articles were not verified as full text | repair_then_reconfirm |
| Renewables Now | 2026-08-21 | healthy | 458 | 0 | 20 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-21 | healthy | 7557 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-21 | healthy | 5195 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-21 | healthy | 684 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-21 | healthy | 650 | 0 | 6 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-21 | healthy | 919 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-21 | healthy | 1440 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-21 | healthy | 925 | 0 | 2 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-21 | zero | 0 | 0 | 0 | 26 | 24 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-21 | zero | 0 | 0 | 0 | 11 | 14 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-21 | healthy | 1285 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-21 | zero | 0 | 0 | 0 | 26 | 23 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-21 | healthy | 739 | 0 | 1 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-21 | zero | 0 | 0 | 0 | 25 | 22 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-21 | degraded | 1112 | 1 | 2 | 1 | 2 | 1 articles were not verified as full text | repair_then_reconfirm |
| 索比光伏 | 2026-08-21 | healthy | 480 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
