from pydantic import BaseModel, Field

from app.agent.prompts import SYSTEM_DIALOGUE
from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.agent_state import AgentMessage
from app.schemas.llm import LLMMessage
from app.schemas.memory import MemoryEntry
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


class DialogueDeepSeekOutput(BaseModel):
    assistant_message: str


def _build_dialogue_prompt(inp: DialogueDeepSeekInput) -> str:
    lines = [SYSTEM_DIALOGUE]

    # Memory section (max 3 entries, 300 chars each)
    if inp.memory_entries:
        lines.append("\n已知长期记忆：")
        for me in inp.memory_entries[:3]:
            snippet = me.content[:300]
            lines.append(f"- {me.frontmatter.name}: {me.frontmatter.description}")
            lines.append(f"  {snippet}")

    if not inp.report_ready:
        # 还有信息需要追问（可能 score_ready 但 report_ready 未达到）
        if inp.score_ready and not inp.report_ready:
            lines.append("基础信息已足够生成初步报告，但诊断质量还需要补充以下信息：")
        else:
            lines.append("以下关键信息尚未收集完成：")

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

        lines.append("严格约束：")
        lines.append("- 必须优先追问上述缺失信息，每轮最多问 1-2 个问题。")
        lines.append("- 不允许声明'信息收集完毕''信息已齐''已安排顾问''24小时联系''请留意电话'。")
        lines.append("- 不允许输出投流预算分配、运营方案、执行计划。")
    else:
        lines.append("关键信息已基本齐备，可以引导用户点击'生成报告'按钮获取完整诊断报告。")
        lines.append("本轮可以做一个简短小结（2-3句话），告诉用户报告会覆盖哪些方面。")

    return "\n".join(lines)


async def dialogue_deepseek_handler(
    inp: DialogueDeepSeekInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        settings = get_settings()
        client = DeepSeekClient()
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
