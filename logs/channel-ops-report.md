# 渠道运维总览

- 生成时间：2026-09-11T08:34:52.204396+08:00
- 渠道数：61
- 健康/正常空闲：39
- 异常渠道：8
- 待处理缺口：340

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-10 | healthy | 1248 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-10 | idle | 0 | 0 | 0 | 0 | 22 | all observed candidates were published outside the target date (2026-08-08 to 2026-09-01) | repair_then_confirm |
| Data Center Knowledge | 2026-09-10 | healthy | 4361 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-10 | healthy | 5240 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-10 | healthy | 3685 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-10 | healthy | 1341 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-10 | zero | 0 | 0 | 0 | 4 | 13 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-10 | healthy | 5925 | 0 | 0 | 0 | 9 | - | repair_then_reconfirm |
| interesting engineering | 2026-09-10 | healthy | 3765 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-10 | healthy | 629 | 0 | 5 | 0 | 3 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-10 | healthy | 8710 | 0 | 0 | 0 | 9 | - | repair_then_reconfirm |
| NE时代 | 2026-09-10 | healthy | 2909 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-10 | healthy | 3247 | 0 | 1 | 0 | 11 | - | repair_then_reconfirm |
| pv magazine | 2026-09-10 | healthy | 2972 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-10 | degraded | 2087 | 1 | 1 | 2 | 14 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-09-10 | zero | 0 | 0 | 0 | 3 | 4 | no target-date articles were collected | repair_then_reconfirm |
| scitechdaily | 2026-09-10 | healthy | 6359 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-10 | healthy | 5937 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| the information | 2026-09-10 | healthy | 299 | 0 | 9 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-10 | healthy | 874 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-10 | healthy | 700 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-10 | healthy | 676 | 0 | 0 | 0 | 6 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-10 | healthy | 1117 | 0 | 0 | 0 | 12 | - | repair_then_reconfirm |
| 中国能源网 | 2026-09-10 | zero | 0 | 0 | 0 | 4 | 20 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-09-10 | zero | 0 | 0 | 0 | 1 | 32 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-09-10 | zero | 0 | 0 | 0 | 4 | 29 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-10 | idle | 0 | 0 | 0 | 0 | 3 | all observed candidates were published outside the target date (2026-09-08 to 2026-09-09) | repair_then_confirm |
| 国际能源网 | 2026-09-10 | zero | 0 | 0 | 0 | 19 | 42 | no target-date articles were collected | repair_then_confirm |
| 少数派 | 2026-09-10 | healthy | 3483 | 0 | 1 | 0 | 1 | - | repair_then_confirm |
| 我爱电车网 | 2026-09-10 | healthy | 807 | 0 | 0 | 0 | 20 | - | repair_then_confirm |
| 电池网 | 2026-09-10 | zero | 0 | 0 | 0 | 1 | 26 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-09-10 | healthy | 1413 | 0 | 1 | 0 | 4 | - | repair_then_reconfirm |
| 索比光伏 | 2026-09-10 | healthy | 785 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
