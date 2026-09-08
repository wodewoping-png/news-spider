# 渠道运维总览

- 生成时间：2026-09-08T17:32:56.885102+08:00
- 渠道数：61
- 健康/正常空闲：41
- 异常渠道：6
- 待处理缺口：317

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-07 | healthy | 1392 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-07 | idle | 0 | 0 | 0 | 0 | 21 | all observed candidates were published outside the target date (2026-08-08 to 2026-09-01) | repair_then_confirm |
| Data Center Knowledge | 2026-09-07 | idle | 0 | 0 | 0 | 0 | 2 | all observed candidates were published outside the target date (2026-08-06 to 2026-09-04) | repair_then_confirm |
| Electrek | 2026-09-07 | healthy | 4706 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-07 | healthy | 4531 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-07 | idle | 0 | 0 | 0 | 0 | 8 | all observed candidates were published outside the target date (2026-08-25 to 2026-09-04) | repair_then_confirm |
| H2 View | 2026-09-07 | zero | 0 | 0 | 0 | 1 | 10 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-07 | healthy | 6973 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| interesting engineering | 2026-09-07 | healthy | 3791 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-07 | healthy | 591 | 0 | 8 | 0 | 3 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-07 | healthy | 5949 | 0 | 0 | 0 | 9 | - | repair_then_reconfirm |
| NE时代 | 2026-09-07 | healthy | 3837 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-07 | healthy | 3596 | 0 | 0 | 0 | 10 | - | repair_then_reconfirm |
| pv magazine | 2026-09-07 | healthy | 2249 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-07 | degraded | 1995 | 1 | 1 | 1 | 12 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-09-07 | healthy | 1358 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-09-07 | healthy | 6603 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-07 | healthy | 5190 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| the information | 2026-09-07 | healthy | 645 | 0 | 1 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-07 | healthy | 682 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-07 | healthy | 659 | 0 | 6 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-07 | healthy | 785 | 0 | 0 | 0 | 6 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-07 | zero | 0 | 0 | 0 | 1 | 11 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-07 | zero | 0 | 0 | 0 | 1 | 17 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-09-07 | idle | 0 | 0 | 0 | 0 | 31 | all observed candidates were published outside the target date (2026-08-20 to 2026-09-04) | repair_then_confirm |
| 北极星储能网 | 2026-09-07 | zero | 0 | 0 | 0 | 1 | 26 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-07 | healthy | 1465 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-07 | zero | 0 | 0 | 0 | 16 | 39 | no target-date articles were collected | repair_then_confirm |
| 少数派 | 2026-09-07 | healthy | 5182 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| 我爱电车网 | 2026-09-07 | healthy | 1055 | 0 | 0 | 0 | 20 | - | repair_then_confirm |
| 电池网 | 2026-09-07 | idle | 0 | 0 | 0 | 0 | 25 | all observed candidates were published outside the target date (2026-07-31 to 2026-09-02) | repair_then_confirm |
| 科学网新闻 | 2026-09-07 | healthy | 798 | 0 | 2 | 0 | 4 | - | repair_then_reconfirm |
| 索比光伏 | 2026-09-07 | healthy | 589 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
