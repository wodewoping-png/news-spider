# 渠道运维总览

- 生成时间：2026-07-30T07:38:05.400874+08:00
- 渠道数：57
- 健康/正常空闲：35
- 异常渠道：8
- 待处理缺口：34

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| electrive | 2026-07-29 | healthy | 3141 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-07-29 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| H2 View | 2026-07-29 | degraded | 781 | 3 | 0 | 2 | 1 | 3 articles were not verified as full text | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-07-29 | healthy | 6047 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| INSIDEEVs | 2026-07-29 | degraded | 109 | 5 | 5 | 1 | 0 | 5 articles were not verified as full text | investigate |
| interesting engineering | 2026-07-29 | healthy | 5171 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| IT之家 | 2026-07-29 | healthy | 614 | 0 | 7 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-07-29 | healthy | 3783 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| perovskite-info | 2026-07-29 | healthy | 4447 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| pv magazine | 2026-07-29 | healthy | 2456 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-07-29 | zero | 0 | 0 | 0 | 2 | 4 | no target-date articles were collected | repair_then_reconfirm |
| Renewables Now | 2026-07-29 | healthy | 457 | 0 | 18 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-07-29 | healthy | 5524 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-07-29 | healthy | 5688 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-07-29 | healthy | 735 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-07-29 | healthy | 723 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-科技 | 2026-07-29 | healthy | 1402 | 0 | 0 | 0 | 2 | - | repair_then_reconfirm |
| 中国能源网 | 2026-07-29 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-07-29 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-07-29 | healthy | 859 | 0 | 0 | 0 | 1 | - | repair_then_confirm |
| 国际能源网 | 2026-07-29 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-07-29 | zero | 0 | 0 | 0 | 1 | 1 | no target-date articles were collected | repair_then_confirm |
| 科学网新闻 | 2026-07-29 | healthy | 871 | 0 | 2 | 0 | 2 | - | repair_then_reconfirm |
| 索比光伏 | 2026-07-29 | healthy | 2220 | 0 | 1 | 0 | 1 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
