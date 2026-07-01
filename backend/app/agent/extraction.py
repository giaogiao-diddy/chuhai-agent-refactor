from app.agent.prompts import SYSTEM_DIALOGUE
from app.schemas.agent_state import AgentMessage
from app.schemas.extraction import ExtractionResult
from app.schemas.llm import LLMMessage
from app.scoring.questionnaire import ALL_QUESTIONS
from app.services.deepseek_client import DeepSeekClient


def build_question_catalog() -> str:
    lines: list[str] = []
    for q in ALL_QUESTIONS:
        if q.kind == "open_text":
            continue  # Q1 不进 answers
        kind_tag = "多选" if q.kind == "multiple_choice" else "单选"
        opts = " ".join(f"{o.id}={o.text}" for o in q.options)
        lines.append(f"{q.id} {q.text} [{kind_tag}]: {opts}")
    return "\n".join(lines)


QUESTION_CATALOG = build_question_catalog()

SYSTEM_EXTRACT_ANSWERS = f"""{SYSTEM_DIALOGUE}

同时从对话中提取结构化信息。输出纯 JSON，不要 markdown。

规则：
1. slots: 字典，key={{"value":"...","confidence":0.9}}。字段: industry, main_product, target_market, overseas_experience, annual_revenue, team_size, sales_team_size, overseas_order_ratio, content_capability, conversion_channel, monthly_budget, consultation_intent。
2. answers: 选择题/多选题答案数组 [{{"question_id":"Q5","option_ids":["C"],"confidence":0.9}}]。只允许以下题库 ID，单选题 option_ids 最多1个，多选题可多个:
{QUESTION_CATALOG}
3. 不确定就不输出该题。Q1的行业/产品信息只写入slots，不放answers。
4. Q5必须尽量输出：有海外客户/订单/询盘→C(少量)，明确10%以上→B，30%以上→A，完全没有→D。
5. reasoning_summary 一句中文总结。
"""


async def extract_from_messages(
    messages: list[AgentMessage],
    history_window: int | None = 12,
) -> ExtractionResult:
    selected = messages if history_window is None else messages[-history_window:]
    user_texts = [m.content for m in selected if m.role in ("user", "assistant")]
    llm_messages = [
        LLMMessage(role="system", content=SYSTEM_EXTRACT_ANSWERS),
        LLMMessage(role="user", content="\n".join(user_texts)),
    ]
    client = DeepSeekClient()
    return await client.chat_json(
        llm_messages, response_model=ExtractionResult, max_tokens=4000, temperature=0.0
    )
