from __future__ import annotations

from .catalog import CandidateSite


MINISTRY_SITES: tuple[CandidateSite, ...] = (
    CandidateSite("most_notices", "科学技术部_通知通告", "全国", "科学技术部",
                  ("https://www.most.gov.cn/tztg/",),
                  ("https://www.most.gov.cn/tztg/202609/t20260908_197283.html",)),
    CandidateSite("mee_public_notices", "生态环境部_公示公告", "全国", "生态环境部",
                  ("https://www.mee.gov.cn/ywdt/gsgg/",), ()),
    CandidateSite("mnr_notices", "自然资源部_通知公告", "全国", "自然资源部",
                  ("https://www.mnr.gov.cn/gk/tzgg/",),
                  ("https://www.mnr.gov.cn/gk/tzgg/202608/t20260824_2936891.html",)),
    CandidateSite("mot_policy_documents", "交通运输部_其他政策性文件", "全国", "交通运输部",
                  ("https://xxgk.mot.gov.cn/2020/zhengce/qtwjlist.html",),
                  ("https://xxgk.mot.gov.cn/2020/jigou/glj/202609/t20260904_4223835.html",)),
    CandidateSite("mwr_notices", "水利部_通知公告", "全国", "水利部",
                  ("https://www.mwr.gov.cn/zw/tzgg/",), ()),
    CandidateSite("moa_public_information", "农业农村部_法定主动公开", "全国", "农业农村部",
                  ("https://www.moa.gov.cn/govpublic/",), ()),
    CandidateSite("mofcom_policy_releases", "商务部_政策发布", "全国", "商务部",
                  ("https://www.mofcom.gov.cn/zcfb/index.html",),
                  ("https://www.mofcom.gov.cn/zcfb/zc/art/2026/art_97e72afd4b7f41dab15603c723ea46a9.html",)),
    CandidateSite("mem_notices", "应急管理部_通知公告", "全国", "应急管理部",
                  ("https://www.mem.gov.cn/gk/tzgg/",),
                  ("https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202609/t20260904_715238.shtml",)),
    CandidateSite("mof_announcements", "财政部_财政部公告", "全国", "财政部",
                  ("https://www.mof.gov.cn/gkml/bulinggonggao/czbgg/",), ()),
    CandidateSite("nda_policy_releases", "国家数据局_政策发布", "全国", "国家数据局",
                  ("https://www.nda.gov.cn/sjj/zwgk/zcfb/list/index_pc_1.html",),
                  ("https://www.nda.gov.cn/sjj/zwgk/zcfb/0708/20260708133949899211227_pc.html",)),
    CandidateSite("samr_antitrust_notices", "市场监管总局_反垄断通知公告", "全国", "国家市场监督管理总局",
                  ("https://www.samr.gov.cn/jzxts/tzgg/index.html",),
                  ("https://www.samr.gov.cn/jzxts/tzgg/zqyj/art/2026/art_0a8b25d52d704b8a902f6bcdb3977995.html",)),
)


READY_MINISTRY_SLUGS = {
    "most_notices", "mnr_notices", "mot_policy_documents",
    "mofcom_policy_releases", "mem_notices", "nda_policy_releases",
    "samr_antitrust_notices",
}
READY_MINISTRY_SITES = tuple(site for site in MINISTRY_SITES if site.slug in READY_MINISTRY_SLUGS)
