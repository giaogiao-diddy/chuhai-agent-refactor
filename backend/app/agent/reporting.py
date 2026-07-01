from app.schemas.agent_state import AgentState
from app.schemas.llm import LLMMessage
from app.schemas.rag import RagDocumentMatch
from app.schemas.report import RawAIReport
from app.services.deepseek_client import DeepSeekClient
from config import get_settings

SYSTEM_REPORT_GENERATION = """你是出海咨询公司的资深顾问。

根据企业的基本盘、评分结果、7维度得分，生成一份诊断报告。输出纯 JSON，不要 markdown。

必须包含以下全部字段，字段名必须完全一致：
summary_conclusion, positioning_assessment, content_assessment, conversion_assessment,
recommended_path, risk_reminder, action_plan_30days,
consultant_guide, sales_followup, consultant_notes

要求：
- 语气专业、具体、可执行，不要空泛鸡汤。
- summary_conclusion ≤ 400 字
- positioning_assessment ≤ 300 字
- content_assessment ≤ 300 字
- conversion_assessment ≤ 300 字
- recommended_path ≤ 250 字
- risk_reminder ≤ 250 字
- action_plan_30days 必须正好 4 条
- consultant_guide 给顾问使用的引导话术
- sales_followup 给顾问使用，包含跟进重点和建议话术
- consultant_notes 给顾问内部使用，不对外展示"""


async def generate_raw_report(
    state: AgentState,
    rag_context: list[RagDocumentMatch] | None = None,
) -> RawAIReport:
    scoring = state.scoring_result
    if scoring is None:
        raise ValueError("缺少 scoring_result，无法生成报告")

    slots = state.slots
    industry = slots.industry.value if slots.industry else "未提供"
    product = slots.main_product.value if slots.main_product else "未提供"
    target = slots.target_market.value if slots.target_market else "未提供"

    dims_str = "\n".join(
        f"{ds.name}: {ds.raw_score}/{ds.max_score}" for ds in scoring.dimension_scores[:7]
    )

    prompt = f"""请根据以下信息生成诊断报告：

行业: {industry}
产品: {product}
目标市场: {target}
Q5分支: {state.branch}
答案数量: {len(state.answers)}

评分结果:
- 总分: {scoring.feasibility_score}/100
- 标签: {scoring.tag} ({scoring.tag_explanation})
- 顾问优先级: {scoring.lead_score}/100 ({scoring.lead_priority})
- 维度分:
{dims_str}
- 优势: {", ".join(scoring.strengths)}
- 风险: {", ".join(scoring.risks)}"""

    if rag_context:
        rag_lines = []
        for i, m in enumerate(rag_context, 1):
            rag_lines.append(f"{i}. [{m.title}] {m.content}")
        rag_block = "\n".join(rag_lines)
        prompt += f"\n\n参考知识:\n{rag_block}"

    settings = get_settings()
    client = DeepSeekClient()
    return await client.chat_json(
        [LLMMessage(role="system", content=SYSTEM_REPORT_GENERATION),
         LLMMessage(role="user", content=prompt)],
        response_model=RawAIReport,
        max_tokens=settings.REPORT_MAX_TOKENS,
        temperature=0.2,
    )
