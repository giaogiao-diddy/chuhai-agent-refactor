from pydantic import BaseModel

from app.agent.prompts import SYSTEM_DIALOGUE
from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.agent_state import AgentMessage
from app.schemas.llm import LLMMessage
from app.services.deepseek_client import DeepSeekClient


class DialogueDeepSeekInput(BaseModel):
    messages: list[AgentMessage]
    missing_items: list[dict] = []
    next_questions: list[str] = []


class DialogueDeepSeekOutput(BaseModel):
    assistant_message: str


def _build_dialogue_prompt(inp: DialogueDeepSeekInput) -> str:
    lines = [SYSTEM_DIALOGUE]
    if inp.missing_items:
        missing_labels = [m.get("label", m.get("question_id", "?")) for m in inp.missing_items]
        lines.append(f"当前缺失关键信息：{'、'.join(missing_labels[:4])}")
        lines.append("必须优先追问上述缺失信息，每轮最多问 1-2 个问题。")
        lines.append("不要在关键信息缺失时给详细投放计划、预算分配或运营执行建议。")
    if inp.next_questions:
        lines.append(f"建议追问方向：{' / '.join(inp.next_questions[:4])}")
    return "\n".join(lines)


async def dialogue_deepseek_handler(
    inp: DialogueDeepSeekInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        client = DeepSeekClient()
        system_prompt = _build_dialogue_prompt(inp)
        llm_messages = [LLMMessage(role="system", content=system_prompt)]
        # LLM 输入只取最近 12 条
        for msg in inp.messages[-12:]:
            llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

        response = await client.chat(llm_messages, max_tokens=256, temperature=0.2)
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
