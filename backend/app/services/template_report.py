"""模板报告拼装 — AI 报告失败的兜底方案

模板输入/输出结构与 AI 报告完全一致，前端不区分来源。
"""


# ── 四种标签的部分报告模板 ──────────────────────────────────────────

_OBSERVE = {
    "tag_explanation": "当前仍处于准备阶段，适合先完成调研、产品梳理和低成本验证。",
    "preliminary_judgment": "综合来看，您的企业目前处于出海早期准备阶段。建议先夯实国内市场基础，完成目标市场调研后，再逐步推进出海计划。",
    "strengths": [
        "对出海有清晰的认知和规划意愿",
        "愿意花时间做好准备工作，不盲目冒进",
    ],
    "risks": [
        "产品标准化程度可能不足，需进一步打磨",
        "对目标市场的政策法规了解有限",
    ],
}

_LIGHT = {
    "tag_explanation": "已具备部分条件，但关键能力尚未完整，适合小预算、轻渠道测试。",
    "preliminary_judgment": "您的企业已迈出出海第一步，部分条件已经就绪。建议通过小规模测试验证产品市场匹配度，逐步积累海外运营经验。",
    "strengths": [
        "已有一定的线上获客经验",
        "对目标市场有初步了解",
    ],
    "risks": [
        "产品标准化程度需要提升",
        "海外交付和售后能力有待验证",
    ],
}

_BASIC = {
    "tag_explanation": "具备一定出海基础，可以进入系统化测试阶段。",
    "preliminary_judgment": "您的企业具备较好的出海基础，核心能力已初步建立。建议选择一到两个目标市场进行系统化测试，为规模化出海积累经验。",
    "strengths": [
        "产品已具备标准化交付能力",
        "团队对海外市场有一定实战经验",
        "业务模式在海外具备可复制性",
    ],
    "risks": [
        "品牌在目标市场的认知度需要建立",
        "供应链的跨境稳定性需要加强",
    ],
}

_PRIORITY = {
    "tag_explanation": "整体条件较成熟，具备较高海外市场开拓潜力。",
    "preliminary_judgment": "您的企业出海条件较为成熟，具备较强的海外市场竞争力。建议加快布局节奏，在核心目标市场建立先发优势。",
    "strengths": [
        "产品高度标准化，适配海外市场需求",
        "团队具备丰富的跨境业务经验",
        "已建立一定海外品牌认知度",
        "拥有稳定的海外渠道和供应链体系",
    ],
    "risks": [
        "快速扩张中需关注本地化合规风险",
        "多市场并进可能导致资源分散",
    ],
}

_SUMMARY_TEMPLATES = {
    "观察准备型": _OBSERVE,
    "轻量试探型": _LIGHT,
    "基础具备型": _BASIC,
    "优先布局型": _PRIORITY,
}


def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板 + 答案变量生成部分报告

    Args:
        total_score: 原始总分 (15-60)
        tag: 标签名称
        answer_summary: 答案摘要 dict，用于模板变量插值

    Returns:
        包含 total_score, tag, tag_explanation, preliminary_judgment,
        strengths, risks, unlock_hint 的 dict
    """
    template = _SUMMARY_TEMPLATES.get(tag, _OBSERVE)
    answer_summary = answer_summary or {}

    # 安全插值：用 .get() 提供默认值，避免 KeyError
    strengths = [
        s.format(**{k: answer_summary.get(k, "") for k in answer_summary})
        for s in template["strengths"]
    ]
    risks = [
        r.format(**{k: answer_summary.get(k, "") for k in answer_summary})
        for r in template["risks"]
    ]
    judgment = template["preliminary_judgment"].format(
        **{k: answer_summary.get(k, "") for k in answer_summary}
    )

    return {
        "total_score": total_score,
        "tag": tag,
        "tag_explanation": template["tag_explanation"],
        "preliminary_judgment": judgment,
        "strengths": strengths,
        "risks": risks,
        "unlock_hint": "提交信息后解锁完整报告，并领取 45 分钟 1 对 1 免费解读。",
    }


# ── 四种标签的完整报告模板 ──────────────────────────────────────────

_FULL_TEMPLATES = {
    "观察准备型": {
        "summary_conclusion": "综合来看，您的企业目前处于出海准备阶段。建议先夯实国内基础，完成目标市场调研和产品出海版本打磨后，再推进出海计划。",
        "dimension_scores": {"公司实力": 14, "业务准备": 12, "市场认知": 10, "执行能力": 12},
        "recommended_path": "建议先通过跨境电商平台进行小规模试水，同时深入研究目标市场的法规与消费习惯。",
        "risk_reminder": "需重点关注产品合规认证和知识产权保护，避免在未充分准备的情况下大规模投入。",
        "action_plan_30days": [
            "完成一份目标市场竞品分析报告",
            "梳理产品出海所需的合规认证清单",
            "注册目标市场的核心商标和域名",
        ],
    },
    "轻量试探型": {
        "summary_conclusion": "您的企业已初步具备出海条件，但部分关键能力仍需打磨。建议以小预算、轻渠道的方式先跑通最小闭环。",
        "dimension_scores": {"公司实力": 16, "业务准备": 15, "市场认知": 14, "执行能力": 14},
        "recommended_path": "建议选择 1-2 个东南亚或日韩市场，通过独立站或平台店铺进行轻量级测试，验证产品市场匹配度。",
        "risk_reminder": "需注意跨境物流时效和售后服务体系搭建，避免因体验差导致市场口碑受损。",
        "action_plan_30days": [
            "确定 1 个首选目标市场并完成基础调研",
            "搭建独立站或入驻跨境电商平台",
            "完成首批小批量货物的跨境物流测试",
        ],
    },
    "基础具备型": {
        "summary_conclusion": "您的企业出海基础较好，核心能力已初步建立。建议系统化推进，在重点市场建立稳定的业务基础。",
        "dimension_scores": {"公司实力": 20, "业务准备": 18, "市场认知": 17, "执行能力": 18},
        "recommended_path": "建议在优势市场深耕，同步探索 1-2 个新市场。可考虑建立本地化团队或合作伙伴网络，提升市场响应速度。",
        "risk_reminder": "需关注多市场运营的资源分配和团队管理，避免扩张过快导致服务质量下降。",
        "action_plan_30days": [
            "完成目标市场的本地化营销方案",
            "建立或对接目标市场的售后服务体系",
            "启动至少一个本地化合作渠道的洽谈",
        ],
    },
    "优先布局型": {
        "summary_conclusion": "您的企业出海条件较为成熟，具备较强的海外市场竞争力。建议加快布局节奏，抢占核心市场的先发优势。",
        "dimension_scores": {"公司实力": 24, "业务准备": 22, "市场认知": 21, "执行能力": 22},
        "recommended_path": "建议采取多市场并进策略，在已验证市场加大投入，同时积极探索高潜力新兴市场。考虑建立本地化运营中心。",
        "risk_reminder": "快速扩张阶段需重点关注多市场合规差异、汇率波动风险和跨文化团队管理。",
        "action_plan_30days": [
            "制定未来 3 个月的海外市场扩张路线图",
            "完成重点市场的本地化团队招聘或合作伙伴签约",
            "启动品牌在目标市场的本地化推广活动",
            "建立海外业务数据监控和复盘机制",
        ],
    },
}


def build_full(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板 + 答案变量生成完整报告

    Args:
        total_score: 原始总分 (15-60)
        tag: 标签名称
        answer_summary: 答案摘要 dict，用于模板变量插值

    Returns:
        包含 summary_conclusion, dimension_scores, recommended_path,
        risk_reminder, action_plan_30days, consultant_guide 的 dict
    """
    template = _FULL_TEMPLATES.get(tag, _FULL_TEMPLATES["观察准备型"])
    answer_summary = answer_summary or {}

    summary = template["summary_conclusion"].format(
        **{k: answer_summary.get(k, "") for k in answer_summary}
    )
    path = template["recommended_path"].format(
        **{k: answer_summary.get(k, "") for k in answer_summary}
    )
    risk = template["risk_reminder"].format(
        **{k: answer_summary.get(k, "") for k in answer_summary}
    )
    action_plan = [
        a.format(**{k: answer_summary.get(k, "") for k in answer_summary})
        for a in template["action_plan_30days"]
    ]

    return {
        "summary_conclusion": summary,
        "dimension_scores": template["dimension_scores"],
        "recommended_path": path,
        "risk_reminder": risk,
        "action_plan_30days": action_plan,
        "consultant_guide": "以上建议供初步参考，具体出海方案请联系企业微信顾问获得 1 对 1 解读。",
    }
