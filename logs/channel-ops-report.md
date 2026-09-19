# 渠道运维总览

- 生成时间：2026-09-19T08:30:47.257937+08:00
- 渠道数：71
- 健康/正常空闲：48
- 异常渠道：9
- 待处理缺口：398

## 需要处理的渠道

| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 4C Offshore | 2026-09-18 | healthy | 1402 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| Batteries News | 2026-09-18 | healthy | 3817 | 0 | 0 | 0 | 24 | - | repair_then_confirm |
| Data Center Knowledge | 2026-09-18 | healthy | 5145 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| Electrek | 2026-09-18 | healthy | 4410 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| electrive | 2026-09-18 | healthy | 4401 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| EnergyTrend储能 | 2026-09-18 | healthy | 1263 | 0 | 0 | 0 | 8 | - | repair_then_confirm |
| H2 View | 2026-09-18 | zero | 0 | 0 | 0 | 5 | 19 | article fetch failures: Cloudflare access challenge (1) | repair_then_reconfirm |
| Informationsdienst Wissenschaft-idw | 2026-09-18 | healthy | 7205 | 0 | 0 | 0 | 11 | - | repair_then_reconfirm |
| interesting engineering | 2026-09-18 | degraded | 3621 | 1 | 0 | 1 | 9 | 1 articles were not verified as full text (public_preview_only) | repair_then_reconfirm |
| IT之家 | 2026-09-18 | healthy | 720 | 0 | 4 | 0 | 3 | - | repair_then_reconfirm |
| MIT Technology Review | 2026-09-18 | healthy | 7408 | 0 | 0 | 0 | 10 | - | repair_then_reconfirm |
| NE时代 | 2026-09-18 | healthy | 3113 | 0 | 0 | 0 | 7 | - | repair_then_confirm |
| perovskite-info | 2026-09-18 | healthy | 2431 | 0 | 0 | 0 | 12 | - | repair_then_reconfirm |
| pv magazine | 2026-09-18 | healthy | 4300 | 0 | 0 | 0 | 7 | - | repair_then_reconfirm |
| pv magazine C&I PV | 2026-09-18 | healthy | 4347 | 0 | 0 | 0 | 18 | - | repair_then_reconfirm |
| Renewables Now | 2026-09-18 | zero | 0 | 0 | 0 | 5 | 10 | article fetch failures: Cloudflare access challenge (1) | repair_then_reconfirm |
| scitechdaily | 2026-09-18 | healthy | 6661 | 0 | 0 | 0 | 1 | - | repair_then_reconfirm |
| Supply Chain Digital | 2026-09-18 | healthy | 4856 | 0 | 0 | 0 | 4 | - | repair_then_confirm |
| the information | 2026-09-18 | healthy | 6659 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 中国核电信息网-国内 | 2026-09-18 | healthy | 669 | 0 | 1 | 0 | 3 | - | repair_then_reconfirm |
| 中国核电信息网-国际 | 2026-09-18 | healthy | 716 | 0 | 3 | 0 | 2 | - | repair_then_reconfirm |
| 中国电力新闻网-新能源 | 2026-09-18 | zero | 0 | 0 | 0 | 1 | 7 | no target-date articles were collected | repair_then_confirm |
| 中国电力新闻网-科技 | 2026-09-18 | zero | 0 | 0 | 0 | 3 | 17 | no target-date articles were collected | repair_then_reconfirm |
| 中国能源网 | 2026-09-18 | degraded | 754 | 0 | 3 | 5 | 26 | 10 article pages failed (access challenge (10)) | repair_then_confirm |
| 光伏测试网 | 2026-09-18 | healthy | 51 | 0 | 1 | 0 | 36 | - | repair_then_confirm |
| 北极星储能网 | 2026-09-18 | zero | 0 | 0 | 0 | 5 | 35 | article fetch failures: access challenge (10) | repair_then_confirm |
| 国际太阳能光伏网 | 2026-09-18 | healthy | 1066 | 0 | 0 | 0 | 3 | - | repair_then_confirm |
| 国际能源网 | 2026-09-18 | zero | 0 | 0 | 0 | 28 | 50 | article fetch failures: ConnectionError (1) | repair_then_confirm |
| 少数派 | 2026-09-18 | healthy | 6241 | 0 | 0 | 0 | 2 | - | repair_then_confirm |
| 我爱电车网 | 2026-09-18 | healthy | 635 | 0 | 2 | 0 | 20 | - | repair_then_confirm |
| 电池网 | 2026-09-18 | idle | 0 | 0 | 0 | 0 | 25 | all observed candidates were published outside the target date (2026-07-20 to 2026-08-30) | repair_then_confirm |
| 科学网新闻 | 2026-09-18 | healthy | 1303 | 0 | 0 | 0 | 4 | - | repair_then_reconfirm |
| 索比光伏 | 2026-09-18 | healthy | 2783 | 0 | 0 | 0 | 3 | - | repair_then_reconfirm |
| 自然资源部—通知公告 | 2026-09-18 | zero | 0 | 0 | 0 | 4 | 3 | no target-date articles were collected | repair_then_confirm |

## 运维闭环

异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。
