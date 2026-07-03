from pydantic import BaseModel

from app.agent.reporting import SYSTEM_REPORT_GENERATION, generate_raw_report
from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.agent_state import AgentState
from app.schemas.llm import LLMMessage
from app.schemas.rag import RagDocumentMatch
from app.schemas.report import RawAIReport
from app.services.deepseek_client import DeepSeekClient
from config import get_settings


class ReportGenerateInput(BaseModel):
    state: AgentState
    rag_context: list[RagDocumentMatch] = []
    audit_feedback: list[str] = []
    escalated: bool = False

    model_config = {"arbitrary_types_allowed": True}


class ReportGenerateOutput(BaseModel):
    raw_report: RawAIReport


def _build_feedback_prompt(state: AgentState, rag_context: list[RagDocumentMatch], feedback: list[str]) -> str:
    scoring = state.scoring_result
    if scoring is None:
        raise ValueError("缺少 scoring_result")

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
        rag_lines = [f"{i}. [{m.title}] {m.content}" for i, m in enumerate(rag_context, 1)]
        prompt += f"\n\n参考知识:\n" + "\n".join(rag_lines)

    if feedback:
        prompt += f"\n\n上一版审计问题（必须修正）：\n" + "\n".join(f"- {f}" for f in feedback)

    return prompt


async def report_generate_deepseek_handler(
    inp: ReportGenerateInput,
    ctx: ToolContext,
) -> ToolResult:
    settings = get_settings()
    max_tokens = settings.REPORT_ESCALATED_MAX_TOKENS if inp.escalated else settings.REPORT_MAX_TOKENS
    try:
        if inp.audit_feedback or inp.escalated:
            prompt = _build_feedback_prompt(inp.state, inp.rag_context, inp.audit_feedback)
            client_kwargs: dict = {}
            if ctx is not None and ctx.provider_base_url: client_kwargs["base_url"] = ctx.provider_base_url
            if ctx is not None and ctx.provider_api_key: client_kwargs["api_key"] = ctx.provider_api_key
            if ctx is not None and ctx.provider_model: client_kwargs["model"] = ctx.provider_model
            client = DeepSeekClient(**client_kwargs)
            raw = await client.chat_json(
                [LLMMessage(role="system", content=SYSTEM_REPORT_GENERATION),
                 LLMMessage(role="user", content=prompt)],
                response_model=RawAIReport,
                max_tokens=max_tokens,
                temperature=0.2,
            )
        else:
            raw = await generate_raw_report(
                inp.state, inp.rag_context or None,
                client_base_url=ctx.provider_base_url if ctx is not None else None,
                client_api_key=ctx.provider_api_key if ctx is not None else None,
                client_model=(ctx.provider_model or None) if ctx is not None else None,
            )

        return ToolResult(data=ReportGenerateOutput(raw_report=raw))
    except ValueError as e:
        msg = str(e)
        if "length" in msg.lower() or "max_token" in msg.lower() or "maximum context" in msg.lower():
            return ToolResult(error=ToolError(
                code=ToolErrorCode.LENGTH_EXCEEDED, message=msg, retryable=True,
            ))
        if "JSON" in msg or "解析" in msg or "validation" in msg.lower():
            return ToolResult(error=ToolError(
                code=ToolErrorCode.STRUCTURED_OUTPUT_ERROR, message=msg, retryable=True,
            ))
        return ToolResult(error=ToolError(
            code=ToolErrorCode.TRANSIENT, message=msg, retryable=True,
        ))
    except Exception as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.TRANSIENT, message=str(e), retryable=True,
        ))
