# 渠道运维总览

- 生成时间：2026-08-08T07:12:54.524232+08:00
- 渠道数：59
- 健康/正常空闲：34
- 异常渠道：11
- 待处理缺口：106

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-07 | zero | 0 | 0 | 0 | 5 | 5 | no target-date articles were collected | repair_then_confirm |
| Batteries News | 2026-08-07 | zero | 0 | 0 | 0 | 2 | 2 | no target-date articles were collected | repair_then_confirm |
| Electrek | 2026-08-07 | healthy | 5010 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-07 | healthy | 2898 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-07 | healthy | 1306 | 0 | 0 | 0 | 5 | - | repair_then_confirm |
| H2 View | 2026-08-07 | degraded | 2139 | 1 | 0 | 5 | 1 | 1 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-07 | healthy | 5871 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| INSIDEEVs | 2026-08-07 | degraded | 122 | 6 | 6 | 10 | 0 | 6 articles were not verified as full text | investigate |
| interesting engineering | 2026-08-07 | degraded | 3648 | 20 | 1 | 2 | 4 | 20 articles were not verified as full text | repair_then_reconfirm |
| IT之家 | 2026-08-07 | healthy | 458 | 0 | 11 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-07 | healthy | 25699 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| NE时代 | 2026-08-07 | healthy | 4754 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| perovskite-info | 2026-08-07 | healthy | 3474 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| pv magazine | 2026-08-07 | healthy | 4511 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-07 | healthy | 3482 | 0 | 0 | 0 | 6 | - | repair_then_reconfirm |
| Renewables Now | 2026-08-07 | healthy | 494 | 0 | 17 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-07 | healthy | 7992 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-07 | healthy | 6189 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-07 | healthy | 606 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-07 | healthy | 801 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-07 | healthy | 1547 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-07 | healthy | 1052 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-07 | zero | 0 | 0 | 0 | 5 | 6 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-08-07 | zero | 0 | 0 | 0 | 10 | 10 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-07 | healthy | 358 | 0 | 20 | 0 | 2 | - | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-07 | healthy | 1037 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-07 | zero | 0 | 0 | 0 | 10 | 9 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-07 | zero | 0 | 0 | 0 | 10 | 8 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-08-07 | zero | 0 | 0 | 0 | 9 | 8 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-07 | healthy | 1027 | 0 | 1 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-07 | zero | 0 | 0 | 0 | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
