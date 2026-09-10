# 渠道运维总览

- 生成时间：2026-09-10T08:56:51.395124+08:00
- 渠道数：61
- 健康/正常空闲：37
- 异常渠道：10
- 待处理缺口：332

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-09 | healthy | 1150 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-09 | zero | 0 | 0 | 0 | 1 | 22 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-09-09 | healthy | 6180 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-09 | healthy | 5303 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-09 | healthy | 3492 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-09 | healthy | 1206 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-09 | zero | 0 | 0 | 0 | 3 | 12 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-09 | zero | 0 | 0 | 0 | 1 | 9 | no target-date articles were collected | repair_then_reconfirm |
| interesting engineering | 2026-09-09 | healthy | 3788 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-09 | idle | 0 | 0 | 0 | 0 | 3 | all observed candidates were published outside the target date (2026-09-10) | repair_then_reconfirm |
| MIT Technology Review | 2026-09-09 | healthy | 7535 | 0 | 0 | 0 | 9 | - | repair_then_reconfirm |
| NE时代 | 2026-09-09 | healthy | 3086 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-09 | zero | 0 | 0 | 0 | 1 | 11 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-09-09 | healthy | 2929 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-09 | degraded | 3062 | 1 | 1 | 1 | 13 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-09-09 | zero | 0 | 0 | 0 | 2 | 3 | no target-date articles were collected | repair_then_reconfirm |
| scitechdaily | 2026-09-09 | healthy | 6230 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-09 | healthy | 5629 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| the information | 2026-09-08 | healthy | 756 | 0 | 2 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-09 | idle | 0 | 0 | 0 | 0 | 3 | all observed candidates were published outside the target date (2026-09-05 to 2026-09-08) | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-09 | healthy | 640 | 0 | 7 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-09 | healthy | 687 | 0 | 0 | 0 | 6 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-09 | zero | 0 | 0 | 0 | 1 | 12 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-09 | zero | 0 | 0 | 0 | 3 | 19 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-09-09 | idle | 0 | 0 | 0 | 0 | 31 | all observed candidates were published outside the target date (2026-08-20 to 2026-09-04) | repair_then_confirm |
| 北极星储能网 | 2026-09-09 | zero | 0 | 0 | 0 | 3 | 28 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-09 | healthy | 897 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-09 | zero | 0 | 0 | 0 | 18 | 41 | no target-date articles were collected | repair_then_confirm |
| 少数派 | 2026-09-09 | healthy | 4481 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| 我爱电车网 | 2026-09-09 | healthy | 913 | 0 | 1 | 0 | 20 | - | repair_then_confirm |
| 电池网 | 2026-09-09 | idle | 0 | 0 | 0 | 0 | 25 | all observed candidates were published outside the target date (2026-08-07 to 2026-09-06) | repair_then_confirm |
| 科学网新闻 | 2026-09-09 | healthy | 1082 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 索比光伏 | 2026-09-09 | healthy | 2079 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
