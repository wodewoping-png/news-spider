# 渠道运维总览

- 生成时间：2026-09-01T09:46:19.601113+08:00
- 渠道数：59
- 健康/正常空闲：38
- 异常渠道：7
- 待处理缺口：273

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-31 | idle | 0 | 0 | 0 | 0 | 7 | all observed candidates were published outside the target date (2026-08-26 to 2026-08-28) | repair_then_confirm |
| Batteries News | 2026-08-31 | zero | 0 | 0 | 0 | 3 | 21 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-31 | healthy | 6275 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-31 | healthy | 6420 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-08-31 | healthy | 2058 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-31 | idle | 0 | 0 | 0 | 0 | 8 | all observed candidates were published outside the target date (2026-08-17 to 2026-08-28) | repair_then_confirm |
| H2 View | 2026-08-31 | degraded | 1402 | 1 | 0 | 1 | 5 | 1 articles were not verified as full text (paywall_or_login_wall) | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-31 | healthy | 5301 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| interesting engineering | 2026-08-31 | degraded | 3477 | 2 | 0 | 2 | 7 | 2 articles were not verified as full text (public_preview_only) | repair_then_reconfirm |
| IT之家 | 2026-08-31 | healthy | 520 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-31 | idle | 0 | 0 | 0 | 0 | 8 | all observed candidates were published outside the target date (2026-08-26 to 2026-09-01) | repair_then_reconfirm |
| NE时代 | 2026-08-31 | healthy | 3074 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-08-31 | healthy | 3282 | 0 | 0 | 0 | 10 | - | repair_then_reconfirm |
| pv magazine | 2026-08-31 | healthy | 3597 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-31 | degraded | 2848 | 1 | 1 | 1 | 10 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-08-31 | healthy | 1327 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-31 | healthy | 7079 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-31 | healthy | 5870 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-31 | healthy | 707 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-31 | healthy | 717 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-31 | healthy | 1029 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-31 | zero | 0 | 0 | 0 | 1 | 6 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-08-31 | healthy | 815 | 0 | 6 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-31 | idle | 0 | 0 | 0 | 0 | 28 | all observed candidates were published outside the target date (2026-08-12 to 2026-08-28) | repair_then_confirm |
| 北极星储能网 | 2026-08-31 | zero | 0 | 0 | 0 | 1 | 21 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-31 | healthy | 1887 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-31 | zero | 0 | 0 | 0 | 8 | 32 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-31 | healthy | 795 | 0 | 0 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-31 | idle | 0 | 0 | 0 | 0 | 24 | all observed candidates were published outside the target date (2026-07-09 to 2026-08-28) | repair_then_confirm |
| 科学网新闻 | 2026-08-31 | healthy | 1091 | 0 | 3 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-31 | healthy | 505 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
