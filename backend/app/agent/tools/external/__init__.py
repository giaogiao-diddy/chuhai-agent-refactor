from app.agent.tools.base import ToolDefinition
from app.agent.tools.external.dialogue import (
    dialogue_deepseek_handler,
    DialogueDeepSeekInput,
    DialogueDeepSeekOutput,
)
from app.agent.tools.external.extraction import (
    extract_answers_deepseek_handler,
    ExtractAnswersDeepSeekInput,
)
from app.agent.tools.registry import ToolRegistry


def register_external_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="dialogue.deepseek",
        description="基于缺失项生成下一轮追问",
        input_model=DialogueDeepSeekInput,
        output_model=DialogueDeepSeekOutput,
        handler=dialogue_deepseek_handler,
        is_read_only=True,
        is_concurrency_safe=False,
        max_retries=2,
        retry_delay_seconds=0.5,
        timeout_seconds=60.0,
    ))
    registry.register(ToolDefinition(
        name="extract_answers.deepseek",
        description="从对话提取 slots / answers / branch",
        input_model=ExtractAnswersDeepSeekInput,
        handler=extract_answers_deepseek_handler,
        is_read_only=True,
        is_concurrency_safe=False,
        max_retries=1,
        retry_delay_seconds=0.5,
        timeout_seconds=60.0,
    ))
