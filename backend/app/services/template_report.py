"""模板报告拼装 — AI 报告失败的兜底方案"""


_BASE_DIMENSION_SCORES = {
    "enterprise_capacity": {"score": 0, "diagnosis": "企业承载力需要结合规模、营收和经营年限继续评估。"},
    "overseas_foundation": {"score": 0, "diagnosis": "出海基础需要结合海外收入、获客方式和目标市场继续评估。"},
    "product_trust_asset": {"score": 0, "diagnosis": "产品信任资产需要结合产品类型、客单价、目录和交付继续评估。"},
    "content_acquisition": {"score": 0, "diagnosis": "内容获客能力需要结合短视频运营和社媒团队继续评估。"},
    "conversion_system": {"score": 0, "diagnosis": "留量转化系统需要结合报价、样品、跟进和发货 SOP 继续评估。"},
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


def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板生成 V2 部分报告。"""
    template = _template_for(tag)
    return {
        "total_score": total_score,
        "display_score": total_score + 43,
        "tag": tag,
        "tag_explanation": template["tag_explanation"],
        "preliminary_judgment": template["preliminary_judgment"],
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
    dimension_scores = {
        key: value.copy()
        for key, value in _BASE_DIMENSION_SCORES.items()
    }
    dimension_scores["enterprise_capacity"]["score"] = min(total_score, 12)
    dimension_scores["overseas_foundation"]["score"] = min(total_score, 20)
    dimension_scores["product_trust_asset"]["score"] = min(total_score, 20)
    dimension_scores["content_acquisition"]["score"] = min(total_score, 8)
    dimension_scores["conversion_system"]["score"] = min(total_score, 8)

    return {
        "summary_conclusion": template["preliminary_judgment"],
        "positioning_assessment": f"定位定生死：{template['positioning_assessment']}",
        "content_assessment": f"内容定江山：{template['content_assessment']}",
        "conversion_assessment": f"SOP 定天下：{template['conversion_assessment']}",
        "dimension_scores": dimension_scores,
        "recommended_path": "建议以强成交人设为主线，先聚焦一个目标市场，跑通定位、内容获客、私域承接和 SOP 转化闭环，再考虑复制到多语种矩阵。",
        "risk_reminder": "本报告仅用于出海经营方向诊断，不承诺具体营收结果，也不替代法律、税务、认证或合规专业意见。",
        "action_plan_30days": [
            "第 1 周：明确目标客户画像、首选市场和核心信任切口。",
            "第 2 周：整理产品目录、工厂实力、客户案例和常见问题素材。",
            "第 3 周：围绕流量内容、营销内容、故事内容各制作一批选题。",
            "第 4 周：建立询盘筛选、报价、样品、跟进和客户管理的最小 SOP。",
        ],
        "consultant_guide": "建议添加企业微信顾问，基于你的行业、目标市场和当前答案获得 45 分钟 1 对 1 解读。",
    }
