from app.agent.tools.base import ToolDefinition
from app.agent.tools.local.question_catalog import (
    question_catalog_handler,
    QuestionCatalogInput,
    QuestionCatalogOutput,
)
from app.agent.tools.local.readiness import (
    readiness_check_handler,
    ReadinessCheckInput,
    ReadinessResult,
)
from app.agent.tools.local.scoring import (
    score_calculate_handler,
    ScoreCalculateInput,
    ScoreCalculateOutput,
)
from app.agent.tools.local.report_tools import (
    report_guard_handler,
    report_split_handler,
    ReportGuardInput,
    ReportGuardOutput,
    ReportSplitInput,
    ReportSplitOutput,
)
from app.agent.tools.registry import ToolRegistry


def register_local_tools(registry: ToolRegistry) -> None:
    registry.register(ToolDefinition(
        name="question_catalog.read",
        description="返回题库摘要、关键问题、display 映射、维度中文名",
        input_model=QuestionCatalogInput,
        output_model=QuestionCatalogOutput,
        handler=question_catalog_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))
    registry.register(ToolDefinition(
        name="readiness.check",
        description="判断是否足够生成报告，返回 missing_items / next_questions",
        input_model=ReadinessCheckInput,
        output_model=ReadinessResult,
        handler=readiness_check_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))
    registry.register(ToolDefinition(
        name="score.calculate",
        description="answers → ScoringResult",
        input_model=ScoreCalculateInput,
        output_model=ScoreCalculateOutput,
        handler=score_calculate_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))
    registry.register(ToolDefinition(
        name="report.split",
        description="RawAIReport + ScoringResult → UserReport + LeadReport",
        input_model=ReportSplitInput,
        output_model=ReportSplitOutput,
        handler=report_split_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))
    registry.register(ToolDefinition(
        name="report.guard",
        description="用户报告安全扫描",
        input_model=ReportGuardInput,
        output_model=ReportGuardOutput,
        handler=report_guard_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))
