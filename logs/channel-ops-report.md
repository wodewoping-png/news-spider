# 渠道运维总览

- 生成时间：2026-08-21T06:58:51.192845+08:00
- 渠道数：59
- 健康/正常空闲：36
- 异常渠道：9
- 待处理缺口：217

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-20 | healthy | 1094 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-08-20 | zero | 0 | 0 | 0 | 17 | 15 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-20 | healthy | 6935 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-20 | healthy | 5666 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-20 | healthy | 3676 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-20 | healthy | 1755 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| H2 View | 2026-08-20 | degraded | 794 | 5 | 0 | 4 | 1 | 5 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-20 | zero | 0 | 0 | 0 | 2 | 5 | no target-date articles were collected | repair_then_reconfirm |
| interesting engineering | 2026-08-20 | degraded | 3760 | 1 | 1 | 1 | 4 | 1 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-20 | healthy | 749 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-20 | healthy | 6855 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| NE时代 | 2026-08-20 | healthy | 3188 | 0 | 0 | 0 | 6 | - | repair_then_confirm |
| perovskite-info | 2026-08-20 | healthy | 2608 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine | 2026-08-20 | healthy | 3748 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-20 | degraded | 6486 | 1 | 1 | 4 | 6 | 1 articles were not verified as full text | repair_then_reconfirm |
| Renewables Now | 2026-08-20 | healthy | 459 | 0 | 18 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-20 | healthy | 6210 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-20 | healthy | 6097 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-20 | healthy | 527 | 0 | 3 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-20 | healthy | 656 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-20 | healthy | 2630 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-20 | healthy | 1732 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-20 | healthy | 1178 | 0 | 0 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-20 | zero | 0 | 0 | 0 | 25 | 23 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-20 | zero | 0 | 0 | 0 | 10 | 13 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-20 | healthy | 1203 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-20 | zero | 0 | 0 | 0 | 25 | 22 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-20 | healthy | 770 | 0 | 0 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-20 | zero | 0 | 0 | 0 | 24 | 21 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-20 | healthy | 967 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-20 | healthy | 830 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
