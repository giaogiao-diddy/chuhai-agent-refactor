from app.schemas.agent_state import AgentState
from app.schemas.report import RawAIReport


def build_template_raw_report(state: AgentState) -> RawAIReport:
    scoring = state.scoring_result
    tag = scoring.tag if scoring else "未知"
    return RawAIReport(
        summary_conclusion=f"该企业属于{tag}，建议在完成基础准备后选择低风险市场先行测试。",
        positioning_assessment="基于当前信息，企业出海定位尚需进一步明确目标市场与产品适配度。",
        content_assessment="企业具备基本的产品信息和行业背景，建议补充海外客户画像和竞品分析。",
        conversion_assessment="当前转化路径尚不完整，建议优先建立询盘承接和外贸跟单基本流程。",
        recommended_path="建议优先以展会或B2B平台验证需求，后续结合独立站和社媒引流。",
        risk_reminder="主要风险包括目标市场不明确、合规认证缺失、交付与售后体系薄弱。",
        action_plan_30days=[
            "明确目标市场和主打产品",
            "获得目标市场合规认证或检测报告",
            "建立英文产品目录和报价体系",
            "启动B2B平台或展会获客测试",
        ],
        consultant_guide="建议添加顾问获取针对性路径规划。",
        sales_followup="根据评分标签，建议顾问重点跟进其出海意愿与预算匹配度。",
        consultant_notes="该报告为模板兜底，AI 生成过程异常。",
    )
