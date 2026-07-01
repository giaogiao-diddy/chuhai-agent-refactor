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

    if inp.missing_items:
        missing_labels = [m.get("label", m.get("question_id", "?")) for m in inp.missing_items]
        missing_asks = [m.get("ask", m.get("label", "?")) for m in inp.missing_items[:2]]
        lines.append(f"当前缺失关键信息：{'、'.join(missing_labels[:4])}")
        lines.append(f"建议追问：{' / '.join(missing_asks)}")
        lines.append("严格约束：")
        lines.append("- 必须优先追问上述缺失信息，每轮最多问 1-2 个问题。")
        lines.append("- 不允许声明'信息已齐''已安排顾问''24小时联系''请留意电话'。")
        lines.append("- 不允许输出投流预算分配、运营方案、执行计划。")
        lines.append("- 只允许围绕缺失项追问，直到所有关键信息补齐。")
        lines.append("不要在关键信息缺失时给详细投放计划、预算分配或运营执行建议。")
    if inp.next_questions:
        lines.append(f"建议追问方向：{' / '.join(inp.next_questions[:4])}")
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
