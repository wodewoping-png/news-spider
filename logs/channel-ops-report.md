# 渠道运维总览

- 生成时间：2026-09-02T08:18:48.958752+08:00
- 渠道数：59
- 健康/正常空闲：38
- 异常渠道：7
- 待处理缺口：280

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-01 | healthy | 1354 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-01 | healthy | 6374 | 0 | 0 | 0 | 21 | - | repair_then_confirm |
| Data Center Knowledge | 2026-09-01 | healthy | 6852 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-01 | healthy | 5085 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-01 | healthy | 3956 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-01 | healthy | 2284 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-01 | zero | 0 | 0 | 0 | 2 | 6 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-01 | healthy | 5533 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| interesting engineering | 2026-09-01 | healthy | 3740 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-01 | healthy | 665 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-01 | healthy | 7745 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| NE时代 | 2026-09-01 | healthy | 3183 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-01 | healthy | 3098 | 0 | 0 | 0 | 10 | - | repair_then_reconfirm |
| pv magazine | 2026-09-01 | healthy | 4067 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-01 | degraded | 3305 | 1 | 1 | 2 | 11 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-09-01 | healthy | 1112 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-09-01 | healthy | 6469 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-01 | healthy | 5649 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-01 | healthy | 707 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-01 | healthy | 812 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-01 | zero | 0 | 0 | 0 | 1 | 5 | no target-date articles were collected | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-01 | zero | 0 | 0 | 0 | 2 | 7 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-01 | healthy | 940 | 0 | 7 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-09-01 | idle | 0 | 0 | 0 | 0 | 28 | all observed candidates were published outside the target date (2026-08-12 to 2026-08-28) | repair_then_confirm |
| 北极星储能网 | 2026-09-01 | zero | 0 | 0 | 0 | 2 | 22 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-01 | healthy | 1027 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-01 | zero | 0 | 0 | 0 | 9 | 33 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-09-01 | healthy | 1217 | 0 | 0 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-09-01 | idle | 0 | 0 | 0 | 0 | 24 | all observed candidates were published outside the target date (2026-07-20 to 2026-08-30) | repair_then_confirm |
| 科学网新闻 | 2026-09-01 | degraded | 600 | 1 | 5 | 1 | 3 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| 索比光伏 | 2026-09-01 | healthy | 847 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
