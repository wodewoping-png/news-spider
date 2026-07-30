# 渠道运维总览

- 生成时间：2026-07-31T07:45:59.999142+08:00
- 渠道数：57
- 健康/正常空闲：32
- 异常渠道：11
- 待处理缺口：43

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| electrive | 2026-07-30 | healthy | 2727 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-07-30 | zero | 0 | 0 | 0 | 2 | 2 | no target-date articles were collected | repair_then_confirm |
| H2 View | 2026-07-30 | degraded | 788 | 5 | 0 | 3 | 1 | 5 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-07-30 | healthy | 5626 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| INSIDEEVs | 2026-07-30 | degraded | 119 | 8 | 8 | 2 | 0 | 8 articles were not verified as full text | investigate |
| interesting engineering | 2026-07-30 | zero | 0 | 0 | 0 | 1 | 3 | no target-date articles were collected | repair_then_reconfirm |
| IT之家 | 2026-07-30 | healthy | 716 | 0 | 5 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-07-30 | healthy | 8264 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| perovskite-info | 2026-07-30 | zero | 0 | 0 | 0 | 1 | 2 | no target-date articles were collected | repair_then_reconfirm |
| pv magazine | 2026-07-30 | healthy | 2223 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-07-30 | zero | 0 | 0 | 0 | 3 | 5 | no target-date articles were collected | repair_then_reconfirm |
| Renewables Now | 2026-07-30 | healthy | 421 | 0 | 16 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-07-30 | healthy | 6401 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-07-30 | healthy | 7607 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-07-30 | healthy | 560 | 0 | 3 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-07-30 | healthy | 856 | 0 | 3 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-科技 | 2026-07-30 | healthy | 1738 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| 中国能源网 | 2026-07-30 | zero | 0 | 0 | 0 | 2 | 2 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-07-30 | zero | 0 | 0 | 0 | 2 | 2 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-07-30 | healthy | 1520 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| 国际能源网 | 2026-07-30 | zero | 0 | 0 | 0 | 2 | 2 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-07-30 | zero | 0 | 0 | 0 | 2 | 2 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-07-30 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-07-30 | healthy | 1080 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-07-30 | healthy | 2488 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
