"""模板报告拼装 — AI 报告失败的兜底方案"""


_BASE_DIMENSION_SCORES = {
    "enterprise_capacity": {
        "title": "企业承载力",
        "score": 0,
        "max_score": 12,
        "diagnosis": "企业承载力需要结合规模、营收和经营年限继续评估。",
        "weak_points": ["规模、营收和经营年限决定能否持续承接海外机会。"],
        "next_action": "先明确当前团队、资金和决策链能支持多大范围的轻资产测试。",
    },
    "overseas_foundation": {
        "title": "出海基础",
        "score": 0,
        "max_score": 20,
        "diagnosis": "出海基础需要结合海外收入、获客方式、目标市场和出海动机继续评估。",
        "weak_points": ["海外收入、获客渠道和市场选择共同决定第一站验证效率。"],
        "next_action": "聚焦一个更有机会建立信任溢价的区域，先做轻资产内容测试。",
    },
    "product_trust_asset": {
        "title": "信任资产",
        "score": 0,
        "max_score": 12,
        "diagnosis": "信任资产需要结合产品类型、客单价和 Catalog 完整度继续评估。",
        "weak_points": ["Catalog、案例和产品价值表达不足时，海外客户很难快速建立信任。"],
        "next_action": "优先整理多语言产品目录、核心卖点和可展示的交付证据。",
    },
    "content_acquisition": {
        "title": "内容获客",
        "score": 0,
        "max_score": 8,
        "diagnosis": "内容获客能力需要结合短视频运营经验和社媒团队配置继续评估。",
        "weak_points": ["缺少稳定内容生产系统时，容易陷入算法奴隶和偶发流量。"],
        "next_action": "先搭建流量内容、营销内容、故事内容的最小选题库。",
    },
    "conversion_system": {
        "title": "转化交付系统",
        "score": 0,
        "max_score": 16,
        "diagnosis": "转化交付系统需要结合业务 SOP、物流、交付稳定性和跨境交易准备继续评估。",
        "weak_points": ["询盘筛选、铂金跟进、交付稳定和合规资料会直接影响成交兑现。"],
        "next_action": "建立火眼金睛筛选问题、跟进节奏、样品流程和交付合规清单。",
    },
}


_DIMENSION_QUESTION_IDS = {
    "enterprise_capacity": {2, 3, 4},
    "overseas_foundation": {5, 6, 13, 14, 15},
    "product_trust_asset": {7, 8, 9},
    "content_acquisition": {10, 11},
    "conversion_system": {12, 16, 17, 18},
}


_SUMMARY_TEMPLATES = {
    "观察准备型": {
        "tag_explanation": "出海基础尚浅，建议先从定位梳理和轻量内容测试开始。",
        "preliminary_judgment": "当前更适合先完成行业定位、目标客户画像和产品信任资产梳理，不建议一开始就重投入铺市场。",
        "positioning_assessment": "定位层面需要先明确卖给谁、主攻哪个区域、用什么差异化理由获得信任。",
        "content_assessment": "内容层面建议先把工厂、产品、案例和交付能力整理成可被海外客户理解的素材。",
        "conversion_assessment": "转化层面需要从报价、样品、跟进和发货四个基础动作建立最小 SOP。",
        "strengths": ["已经开始关注出海机会", "适合通过轻资产方式低成本验证"],
        "risks": ["目标市场和客户画像可能还不够清晰", "内容资产和转化承接体系尚未成型"],
    },
    "轻量试探型": {
        "tag_explanation": "已具备部分条件，可启动强成交人设内容矩阵进行低成本验证。",
        "preliminary_judgment": "已经具备启动轻资产出海测试的基础，下一步重点不是扩大投入，而是跑通定位、内容和留量承接的小闭环。",
        "positioning_assessment": "定位层面已有一定基础，但需要进一步聚焦首个目标市场和最容易成交的客户类型。",
        "content_assessment": "内容层面适合先建立强成交人设，用产品实力、专业判断和客户案例形成信任。",
        "conversion_assessment": "转化层面需要把询盘筛选、百问百答和跟进节奏标准化，避免流量进来后接不住。",
        "strengths": ["具备轻量验证海外市场的起点", "产品或团队已有一定可表达的信任基础"],
        "risks": ["内容获客容易停留在零散发布", "缺少标准化跟进会降低线索转化效率"],
    },
    "基础具备型": {
        "tag_explanation": "基础条件较好，适合系统化推进短视频出海获客体系。",
        "preliminary_judgment": "你的出海基础较好，适合从单点尝试升级为强成交人设闭环：定位更聚焦、内容更稳定、转化 SOP 更标准。",
        "positioning_assessment": "定位层面应围绕高意向客户、核心区域和差异化信任切口建立稳定表达。",
        "content_assessment": "内容层面可以构建流量内容、营销内容、故事内容三类素材，提高海外客户信任效率。",
        "conversion_assessment": "转化层面需要完善线索筛选、样品流程、跟进节奏和客户管理 SOP。",
        "strengths": ["企业基础和产品条件具备系统化推进空间", "适合用内容矩阵提升海外获客效率"],
        "risks": ["如果缺少持续内容节奏，获客会不稳定", "如果 SOP 不统一，团队成交能力难以复制"],
    },
    "优先布局型": {
        "tag_explanation": "整体条件成熟，可进行多语种矩阵布局和规模化获客。",
        "preliminary_judgment": "整体条件已经较成熟，适合从单账号、单市场测试升级到多语种矩阵和规模化转化体系。",
        "positioning_assessment": "定位层面可以围绕核心市场建立主账号心智，再复制到小语种区域。",
        "content_assessment": "内容层面应沉淀可复制的选题、脚本和案例库，形成多语种矩阵的生产标准。",
        "conversion_assessment": "转化层面要把销冠经验沉淀为 SOP，配合 CRM 和客户分层提升复购与转介绍。",
        "strengths": ["具备更快推进海外市场布局的基础", "适合从强成交人设走向多语种内容矩阵"],
        "risks": ["多市场并行可能造成资源分散", "SOP 不标准会放大团队协同成本"],
    },
}


def _template_for(tag: str) -> dict:
    return _SUMMARY_TEMPLATES.get(tag, _SUMMARY_TEMPLATES["观察准备型"])


def _answers_from_summary(answer_summary: dict) -> list[dict]:
    if not isinstance(answer_summary, dict):
        return []
    answers = answer_summary.get("answers", [])
    if not isinstance(answers, list):
        return []
    return answers


def _report_memories_from_summary(answer_summary: dict) -> list[dict]:
    if not isinstance(answer_summary, dict):
        return []
    memories = answer_summary.get("report_memories", [])
    if not isinstance(memories, list):
        return []
    return [
        item
        for item in memories
        if isinstance(item, dict) and item.get("report_memory")
    ]


def _extract_industry(answer_summary: dict) -> str:
    for item in _answers_from_summary(answer_summary):
        if item.get("question_id") == 1:
            industry = str(item.get("answer_text") or "").strip()
            if industry:
                return industry
    return "当前行业"


def _memory_text(answer_summary: dict, question_ids: set[int], fallback: str, limit: int = 260) -> str:
    texts = [
        str(item.get("report_memory") or "").strip()
        for item in _report_memories_from_summary(answer_summary)
        if item.get("question_id") in question_ids
    ]
    text = "；".join(item for item in texts if item)
    if not text:
        return fallback
    return text[:limit] + ("。" if not text[:limit].endswith(("。", "！", "？")) else "")


def _memory_by_question(answer_summary: dict, question_id: int) -> str:
    for item in _report_memories_from_summary(answer_summary):
        if item.get("question_id") == question_id:
            return str(item.get("report_memory") or "").strip()
    return ""


def _calculate_dimension_scores(answer_summary: dict) -> dict:
    answers = _answers_from_summary(answer_summary)
    result = {
        key: value.copy()
        for key, value in _BASE_DIMENSION_SCORES.items()
    }
    for dimension, question_ids in _DIMENSION_QUESTION_IDS.items():
        result[dimension]["score"] = sum(
            int(item.get("score", 0) or 0)
            for item in answers
            if item.get("question_id") in question_ids and int(item.get("score", 0) or 0) > 0
        )
    return result


def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板生成 V2 部分报告。"""
    template = _template_for(tag)
    display_score = total_score + 43
    industry = _extract_industry(answer_summary)
    memory_positioning = _memory_text(
        answer_summary,
        {2, 3, 4, 5, 6, 7, 8, 13, 14, 15},
        template["preliminary_judgment"],
        140,
    )
    memory_content = _memory_text(
        answer_summary,
        {9, 10, 11},
        template["risks"][0],
        120,
    )
    memory_conversion = _memory_text(
        answer_summary,
        {12, 16, 17, 18},
        template["risks"][1],
        120,
    )
    preliminary_judgment = (
        f"结合{industry}的答题情况，当前最需要先补齐定位、信任资产和转化交付的最小闭环。{memory_positioning}"
    )
    tag_explanation = template["tag_explanation"]
    return {
        "hero": {
            "score": display_score,
            "tag": tag,
            "one_sentence_judgment": preliminary_judgment,
            "core_contradiction": tag_explanation,
        },
        "key_findings": [
            {"title": "定位卡点", "content": memory_positioning},
            {"title": "内容短板", "content": memory_content},
            {"title": "转化风险", "content": memory_conversion},
        ],
        "total_score": total_score,
        "display_score": display_score,
        "tag": tag,
        "tag_explanation": tag_explanation,
        "preliminary_judgment": preliminary_judgment,
        "positioning_assessment": template["positioning_assessment"],
        "content_assessment": template["content_assessment"],
        "conversion_assessment": template["conversion_assessment"],
        "strengths": template["strengths"],
        "risks": template["risks"],
        "unlock_hint": "提交信息后解锁完整报告，并领取 45 分钟 1 对 1 免费解读。",
    }


def build_full(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板生成 V2 完整报告。"""
    template = _template_for(tag)
    dimension_scores = _calculate_dimension_scores(answer_summary)
    industry = _extract_industry(answer_summary)
    positioning_memory = _memory_text(
        answer_summary,
        {2, 3, 4, 5, 6, 7, 8, 13, 14, 15},
        template["positioning_assessment"],
    )
    content_memory = _memory_text(
        answer_summary,
        {9, 10, 11},
        template["content_assessment"],
    )
    conversion_memory = _memory_text(
        answer_summary,
        {12, 16, 17, 18},
        template["conversion_assessment"],
    )
    catalog_memory = _memory_by_question(answer_summary, 9)
    sop_memory = _memory_by_question(answer_summary, 12)
    delivery_memory = _memory_by_question(answer_summary, 17)
    compliance_memory = _memory_by_question(answer_summary, 18)

    positioning = f"定位定生死：结合{industry}的答题结果，当前不是简单缺客户，而是目标市场、客户画像和价值表达还没有形成清晰锚点。{positioning_memory} 现阶段应避免停留在价值耗散的卖货表达，优先把产品方案、适用场景和目标客户问题打包成更清晰的价值聚合叙事。"
    content = f"内容定江山：{content_memory} 建议围绕信任三位一体搭建内容资产，先把 Catalog、工厂实力、产品细节、案例和交付证据整理成海外客户能看懂的素材，让客户先看见专业度，再相信交付力。"
    conversion = f"SOP 定天下：{conversion_memory} 需要用火眼金睛筛选、铂金跟进和交付与合规防线，把询盘从热闹流量变成可管理机会，尤其要先跑通报价、样品、跟单、物流和收款资料。"
    risk_reminder = (
        "本报告仅用于出海经营方向诊断，不承诺具体营收结果，也不替代法律、税务、认证或合规专业意见。"
        f"{delivery_memory or '交付稳定性需要提前验证。'}"
        f"{compliance_memory or '跨境收款、合同、认证和本地政策资料需要做基础准备。'}"
    )

    return {
        "diagnosis_cards": [
            {"title": "定位", "content": positioning},
            {"title": "内容", "content": content},
            {"title": "转化", "content": conversion},
        ],
        "strategy_path": {
            "positioning": [
                "锁定最容易成交的目标客户",
                "选择一个首站目标市场",
                "提炼卖什么价值和差异化信任理由",
                "避免用低价和泛渠道消耗优势",
            ],
            "content": [
                "用流量内容解决被看见",
                "用营销内容证明专业度",
                "用故事内容建立选择倾向",
                "沉淀为多语种素材池",
            ],
            "conversion": [
                "用火眼金睛筛选高意向询盘",
                "用百问百答降低沟通成本",
                "用铂金跟进稳定推进成交",
                "用交付清单兑现信任",
            ],
        },
        "risk_cards": [
            {"title": "交付风险", "content": delivery_memory or "交付周期、质检、售后和大单承接能力需要先被标准化，否则成交后容易透支信任。"},
            {"title": "Catalog 风险", "content": catalog_memory or "缺少多语言 Catalog 和产品证据时，海外客户只能靠零散图文判断，信任建立会变慢。"},
            {"title": "内容断档风险", "content": "如果没有稳定选题和脚本 SOP，内容容易停留在偶发更新，难以沉淀获客资产。"},
            {"title": "合规准备风险", "content": compliance_memory or "跨境收款、合同、发票、认证或本地政策资料需做基础准备，本报告不替代专业合规意见。"},
        ],
        "summary_conclusion": template["preliminary_judgment"],
        "positioning_assessment": positioning,
        "content_assessment": content,
        "conversion_assessment": conversion,
        "dimension_scores": dimension_scores,
        "recommended_path": "建议以强成交人设为主线，先聚焦一个目标市场，跑通定位、内容获客、私域承接和 SOP 转化闭环，再考虑复制到多语种矩阵。",
        "risk_reminder": risk_reminder,
        "action_plan_30days": [
            "第1-7天：完成用户画像、首选市场和强成交人设定位梳理，明确第一批内容只服务哪类客户。",
            f"第8-14天：整理多语言 Catalog、工厂实力、客户案例、FAQ 和交付证据，形成信任资产包。{catalog_memory}",
            "第15-21天：围绕流量内容、营销内容、故事内容各制作一批选题，并用自然询盘验证市场反应。",
            f"第22-30天：建立火眼金睛筛选、报价、样品、铂金跟进、物流交付和基础合规资料清单。{sop_memory}{delivery_memory}{compliance_memory}",
        ],
        "consultant_guide": "添加企业微信顾问后，可基于你的行业、答案和当前短板，获得 45 分钟 1 对 1 报告解读。",
    }
