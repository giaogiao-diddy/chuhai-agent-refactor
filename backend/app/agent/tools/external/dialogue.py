from pydantic import BaseModel, Field

from app.agent.prompts import SYSTEM_DIALOGUE
from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.agent_state import AgentMessage, AgentState
from app.schemas.llm import LLMMessage
from app.schemas.memory import MemoryEntry
from app.schemas.readiness import ReadinessResult
from app.services.deepseek_client import DeepSeekClient
from config import get_settings


class DialogueDeepSeekInput(BaseModel):
    messages: list[AgentMessage]
    missing_items: list[dict] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    memory_entries: list[MemoryEntry] = Field(default_factory=list)
    score_ready: bool = False
    report_ready: bool = False
    report_missing_items: list[dict] = Field(default_factory=list)
    slots_summary: dict = Field(default_factory=dict)
    answered_question_ids: list[str] = Field(default_factory=list)


class DialogueDeepSeekOutput(BaseModel):
    assistant_message: str


_SLOT_LABELS = {
    "industry": "行业", "main_product": "主营产品", "target_market": "目标市场",
    "overseas_experience": "海外经验", "annual_revenue": "年营收", "team_size": "团队规模",
    "sales_team_size": "外贸团队规模", "overseas_order_ratio": "海外订单占比",
    "content_capability": "内容能力", "conversion_channel": "转化渠道",
    "monthly_budget": "月预算", "consultation_intent": "咨询意向",
}


def _build_slots_summary(state: AgentState) -> dict:
    """从 AgentState.slots 构建前端安全的结构化画像摘要。"""
    summary: dict = {}
    slots = state.slots
    for key, label in _SLOT_LABELS.items():
        sv = getattr(slots, key, None)
        if sv is not None and sv.value is not None and str(sv.value).strip():
            summary[label] = str(sv.value).strip()
    return summary


def _build_dialogue_input(
    state: AgentState,
    readiness: ReadinessResult | None,
    memory_entries: list[MemoryEntry],
) -> DialogueDeepSeekInput:
    """统一构造 dialogue input，供 streaming 和 non-streaming 共用。"""
    return DialogueDeepSeekInput(
        messages=state.messages,
        missing_items=[m.model_dump() for m in readiness.missing_items] if readiness else [],
        next_questions=readiness.next_questions if readiness else [],
        memory_entries=memory_entries,
        score_ready=readiness.score_ready if readiness else False,
        report_ready=readiness.report_ready if readiness else False,
        report_missing_items=[m.model_dump() for m in readiness.report_missing_items] if readiness else [],
        slots_summary=_build_slots_summary(state),
        answered_question_ids=sorted(state.answers.keys()),
    )


def _build_dialogue_prompt(inp: DialogueDeepSeekInput) -> str:
    lines = [SYSTEM_DIALOGUE]

    # ── 结构化画像摘要 ──
    if inp.slots_summary:
        lines.append("\n【当前企业画像（确定性数据，以本摘要为准，不得编造）】")
        for label, value in inp.slots_summary.items():
            lines.append(f"- {label}: {value}")

    if inp.answered_question_ids:
        lines.append(f"\n【已收集题号】{'、'.join(inp.answered_question_ids)}")

    # ── Memory ──
    if inp.memory_entries:
        lines.append("\n已知长期记忆：")
        for me in inp.memory_entries[:3]:
            snippet = me.content[:300]
            lines.append(f"- {me.frontmatter.name}: {me.frontmatter.description}")
            lines.append(f"  {snippet}")

    # ── 缺失项驱动 ──
    has_missing = bool(inp.missing_items or inp.report_missing_items)

    if has_missing:
        if inp.score_ready and not inp.report_ready:
            lines.append("\n基础信息已足够生成初步报告，但诊断质量还需要补充以下信息：")
        else:
            lines.append("\n以下关键信息尚未收集完成：")

        if inp.report_missing_items:
            rmi_labels = [m.get("label", m.get("question_id", "?")) for m in inp.report_missing_items]
            rmi_asks = [m.get("ask", m.get("label", "?")) for m in inp.report_missing_items[:2]]
            lines.append(f"还需了解：{'、'.join(rmi_labels[:4])}")
            if rmi_asks:
                lines.append(f"建议追问：{' / '.join(rmi_asks)}")

        if inp.missing_items and not inp.score_ready:
            missing_labels = [m.get("label", m.get("question_id", "?")) for m in inp.missing_items]
            missing_asks = [m.get("ask", m.get("label", "?")) for m in inp.missing_items[:2]]
            lines.append(f"当前缺失关键信息：{'、'.join(missing_labels[:4])}")
            lines.append(f"建议追问：{' / '.join(missing_asks)}")

        # 优先追问 next_questions 第一条
        if inp.next_questions:
            lines.append(f"本轮优先追问：{inp.next_questions[0]}")
            if len(inp.next_questions) > 1:
                lines.append(f"备选追问：{' / '.join(inp.next_questions[1:3])}")

        lines.append("\n【严格约束】")
        lines.append("- 禁止声明'信息收集完毕''信息已齐''已安排顾问''24小时联系''请留意电话''请添加微信'。")
        lines.append("- 禁止输出投流预算分配、运营方案、执行计划。")
        lines.append("- 每轮只问 1-2 个问题，优先追问上述建议。")
        lines.append("- 不允许根据最近聊天编造产品、市场、团队信息；必须以【当前企业画像】为准。")
        lines.append("- 不能让用户添加顾问微信。")
    else:
        lines.append("\n关键信息已基本齐备，可以引导用户点击'生成报告'按钮获取完整诊断报告。")
        lines.append("本轮可以做一个简短小结（2-3句话），告诉用户报告会覆盖哪些方面。")
        lines.append("禁止让用户添加微信或联系顾问。")

    return "\n".join(lines)


def _get_client(ctx: ToolContext | None) -> DeepSeekClient:
    if ctx is not None and ctx.provider_base_url and ctx.provider_api_key:
        return DeepSeekClient(base_url=ctx.provider_base_url, api_key=ctx.provider_api_key, model=ctx.provider_model or None)
    return DeepSeekClient()


async def dialogue_deepseek_handler(
    inp: DialogueDeepSeekInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        settings = get_settings()
        client = _get_client(ctx)
        system_prompt = _build_dialogue_prompt(inp)
        llm_messages = [LLMMessage(role="system", content=system_prompt)]
        for msg in inp.messages[-settings.DIALOGUE_HISTORY_WINDOW:]:
            llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

        response = await client.chat(
            llm_messages,
            max_tokens=settings.DIALOGUE_MAX_TOKENS,
            temperature=settings.DIALOGUE_TEMPERATURE,
        )
        assistant_text = response.content.strip()
        if not assistant_text:
            return ToolResult(error=ToolError(
                code=ToolErrorCode.TRANSIENT,
                message="模型返回空内容",
                retryable=True,
            ))

        return ToolResult(data=DialogueDeepSeekOutput(assistant_message=assistant_text))
    except Exception as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.TRANSIENT,
            message=f"对话生成失败: {e}",
            retryable=True,
        ))
