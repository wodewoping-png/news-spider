# 渠道运维总览

- 生成时间：2026-09-03T08:43:09.141459+08:00
- 渠道数：59
- 健康/正常空闲：38
- 异常渠道：7
- 待处理缺口：287

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-02 | healthy | 997 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-02 | idle | 0 | 0 | 0 | 0 | 21 | all observed candidates were published outside the target date (2026-08-08 to 2026-09-01) | repair_then_confirm |
| Data Center Knowledge | 2026-09-02 | healthy | 6676 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-02 | healthy | 5372 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| electrive | 2026-09-02 | healthy | 4641 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-02 | healthy | 2132 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-02 | zero | 0 | 0 | 0 | 3 | 7 | no target-date articles were collected | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-02 | healthy | 4725 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| interesting engineering | 2026-09-02 | healthy | 3742 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| IT之家 | 2026-09-02 | healthy | 691 | 0 | 7 | 0 | 2 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-02 | healthy | 16701 | 0 | 0 | 0 | 8 | - | repair_then_reconfirm |
| NE时代 | 2026-09-02 | healthy | 3076 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-02 | healthy | 3984 | 0 | 0 | 0 | 10 | - | repair_then_reconfirm |
| pv magazine | 2026-09-02 | healthy | 4822 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-02 | healthy | 2648 | 0 | 0 | 0 | 11 | - | repair_then_reconfirm |
| Renewables Now | 2026-09-02 | healthy | 1421 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| scitechdaily | 2026-09-02 | healthy | 6708 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-02 | healthy | 4836 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-02 | healthy | 807 | 0 | 3 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-02 | healthy | 640 | 0 | 4 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-02 | healthy | 698 | 0 | 0 | 0 | 5 | - | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-02 | zero | 0 | 0 | 0 | 3 | 8 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-02 | zero | 0 | 0 | 0 | 1 | 14 | no target-date articles were collected | repair_then_confirm |
| 光伏测试网 | 2026-09-02 | zero | 0 | 0 | 0 | 1 | 29 | no target-date articles were collected | repair_then_confirm |
| 北极星储能网 | 2026-09-02 | zero | 0 | 0 | 0 | 3 | 23 | no target-date articles were collected | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-02 | healthy | 1242 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-02 | zero | 0 | 0 | 0 | 10 | 34 | no target-date articles were collected | repair_then_confirm |
| 我爱电车网 | 2026-09-02 | zero | 0 | 0 | 0 | 1 | 20 | no target-date articles were collected | repair_then_confirm |
| 电池网 | 2026-09-02 | healthy | 614 | 0 | 0 | 0 | 24 | - | repair_then_confirm |
| 科学网新闻 | 2026-09-02 | healthy | 930 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |
| 索比光伏 | 2026-09-02 | healthy | 684 | 0 | 2 | 0 | 3 | - | repair_then_reconfirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
