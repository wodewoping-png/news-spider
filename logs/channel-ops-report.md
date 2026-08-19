# 渠道运维总览

- 生成时间：2026-08-20T06:54:48.532561+08:00
- 渠道数：59
- 健康/正常空闲：37
- 异常渠道：8
- 待处理缺口：211

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-08-19 | healthy | 930 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-08-19 | zero | 0 | 0 | 0 | 16 | 14 | no target-date articles were collected | repair_then_confirm |
| Data Center Knowledge | 2026-08-19 | healthy | 5947 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-08-19 | healthy | 4590 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| electrive | 2026-08-19 | healthy | 5353 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-08-19 | healthy | 1388 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| H2 View | 2026-08-19 | degraded | 873 | 5 | 0 | 3 | 1 | 5 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-08-19 | zero | 0 | 0 | 0 | 1 | 4 | no target-date articles were collected | repair_then_reconfirm |
| interesting engineering | 2026-08-19 | healthy | 3668 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| IT之家 | 2026-08-19 | healthy | 767 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-08-19 | healthy | 16159 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| NE时代 | 2026-08-19 | healthy | 2828 | 0 | 0 | 0 | 6 | - | repair_then_confirm |
| perovskite-info | 2026-08-19 | healthy | 4277 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine | 2026-08-19 | healthy | 3828 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-08-19 | degraded | 2234 | 1 | 1 | 3 | 6 | 1 articles were not verified as full text | repair_then_reconfirm |
| Renewables Now | 2026-08-19 | healthy | 495 | 0 | 20 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-08-19 | healthy | 7211 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-08-19 | healthy | 7219 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-08-19 | healthy | 456 | 0 | 3 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-08-19 | healthy | 745 | 0 | 3 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-08-19 | healthy | 503 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-08-19 | healthy | 1484 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 中国能源网 | 2026-08-19 | healthy | 820 | 0 | 2 | 0 | 13 | - | repair_then_confirm |
| 光伏测试网 | 2026-08-19 | zero | 0 | 0 | 0 | 24 | 22 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-08-19 | zero | 0 | 0 | 0 | 9 | 12 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-08-19 | healthy | 1133 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-08-19 | zero | 0 | 0 | 0 | 24 | 21 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-08-19 | healthy | 672 | 0 | 2 | 0 | 19 | - | repair_then_confirm |
| 电池网 | 2026-08-19 | zero | 0 | 0 | 0 | 23 | 20 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-08-19 | healthy | 1113 | 0 | 1 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-08-19 | healthy | 455 | 0 | 3 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
