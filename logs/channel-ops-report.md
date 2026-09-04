# 渠道运维总览

- 生成时间：2026-09-04T08:40:35.397343+08:00
- 渠道数：59
- 健康/正常空闲：36
- 异常渠道：9
- 待处理缺口：296

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-03 | healthy | 1073 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-03 | idle | 0 | 0 | 0 | 0 | 21 | all observed candidates were published outside the target date (2026-08-08 to 2026-09-01) | repair_then_confirm |
| Data Center Knowledge | 2026-09-03 | healthy | 5714 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-03 | healthy | 4283 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-03 | healthy | 4167 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-03 | healthy | 1755 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-03 | zero | 0 | 0 | 0 | 4 | 8 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-03 | zero | 0 | 0 | 0 | 1 | 8 | no target-date articles were collected | repair_then_reconfirm |
| interesting engineering | 2026-09-03 | healthy | 3634 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-03 | healthy | 550 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-03 | healthy | 5497 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| NE时代 | 2026-09-03 | healthy | 3310 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-03 | healthy | 5374 | 0 | 0 | 0 | 10 | - | repair_then_reconfirm |
| pv magazine | 2026-09-03 | healthy | 5386 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-03 | healthy | 4031 | 0 | 0 | 0 | 11 | - | repair_then_reconfirm |
| Renewables Now | 2026-09-03 | healthy | 1168 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-09-03 | healthy | 7394 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-03 | healthy | 5713 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-03 | healthy | 619 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-03 | healthy | 687 | 0 | 6 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-03 | healthy | 676 | 0 | 0 | 0 | 5 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-03 | zero | 0 | 0 | 0 | 4 | 9 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-03 | zero | 0 | 0 | 0 | 2 | 15 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-09-03 | zero | 0 | 0 | 0 | 2 | 30 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-09-03 | zero | 0 | 0 | 0 | 4 | 24 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-03 | healthy | 1434 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-03 | zero | 0 | 0 | 0 | 11 | 35 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-09-03 | healthy | 623 | 0 | 1 | 0 | 20 | - | repair_then_confirm |
| 电池网 | 2026-09-03 | zero | 0 | 0 | 0 | 1 | 25 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-09-03 | degraded | 844 | 1 | 5 | 1 | 4 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| 索比光伏 | 2026-09-03 | healthy | 390 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
