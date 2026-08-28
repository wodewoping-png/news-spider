# 渠道运维总览

- 生成时间：2026-08-28T14:45:21.458668+08:00
- 渠道数：59
- 健康/正常空闲：38
- 异常渠道：7
- 待处理缺口：254

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-27 | healthy | 1109 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-08-27 | idle | 0 | 0 | 0 | 0 | 18 | all observed candidates were published outside the target date (2026-08-08 to 2026-08-25) | repair_then_confirm |
| Data Center Knowledge | 2026-08-27 | healthy | 10717 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-27 | healthy | 5415 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-08-27 | healthy | 6616 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-27 | healthy | 1541 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-08-27 | degraded | 684 | 5 | 0 | 4 | 3 | 5 articles were not verified as full text (paywall_or_login_wall) | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-27 | healthy | 6017 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| interesting engineering | 2026-08-27 | degraded | 3524 | 1 | 0 | 1 | 5 | 1 articles were not verified as full text (public_preview_only) | repair_then_reconfirm |
| IT之家 | 2026-08-27 | idle | 0 | 0 | 0 | 0 | 2 | all observed candidates were published outside the target date (2026-08-28) | repair_then_reconfirm |
| MIT Technology Review | 2026-08-27 | healthy | 6281 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| NE时代 | 2026-08-27 | healthy | 4101 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-08-27 | zero | 0 | 0 | 0 | 1 | 8 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-08-27 | healthy | 3275 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-27 | degraded | 2557 | 1 | 1 | 3 | 8 | 1 articles were not verified as full text (truncated_ending) | repair_then_reconfirm |
| Renewables Now | 2026-08-27 | healthy | 1598 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-27 | healthy | 5746 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-27 | healthy | 6389 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-27 | healthy | 714 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-27 | healthy | 932 | 0 | 1 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-27 | zero | 0 | 0 | 0 | 1 | 4 | no target-date articles were collected | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-27 | healthy | 759 | 0 | 0 | 0 | 5 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-27 | healthy | 1309 | 0 | 2 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-27 | idle | 0 | 0 | 0 | 0 | 27 | all observed candidates were published outside the target date (2026-08-12 to 2026-08-28) | repair_then_confirm |
| 北极星储能网 | 2026-08-27 | zero | 0 | 0 | 0 | 4 | 19 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-27 | healthy | 2055 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-27 | zero | 0 | 0 | 0 | 4 | 28 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-27 | healthy | 937 | 0 | 0 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-27 | healthy | 526 | 0 | 0 | 0 | 24 | - | repair_then_confirm |
| 科学网新闻 | 2026-08-27 | idle | 0 | 0 | 0 | 0 | 2 | all observed candidates were published outside the target date (2026-08-28) | repair_then_reconfirm |
| 索比光伏 | 2026-08-27 | healthy | 607 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
