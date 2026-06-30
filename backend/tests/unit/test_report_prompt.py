from app.agent.reporting import SYSTEM_REPORT_GENERATION
from app.schemas.report import RawAIReport


def test_report_prompt_contains_raw_ai_report_fields():
    """SYSTEM_REPORT_GENERATION 必须包含 RawAIReport 全部字段名"""
    fields = list(RawAIReport.model_fields.keys())
    for field in fields:
        assert field in SYSTEM_REPORT_GENERATION, (
            f"RawAIReport 字段 '{field}' 未出现在 SYSTEM_REPORT_GENERATION 中"
        )
