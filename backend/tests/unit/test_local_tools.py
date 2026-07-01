import pytest

from app.agent.tools.base import ToolDefinition, ToolErrorCode
from app.agent.tools.executor import ToolExecutor
from app.agent.tools.external import register_external_tools
from app.agent.tools.local import register_local_tools
from app.agent.tools.local.question_catalog import (
    DIMENSION_NAMES,
    QuestionCatalogInput,
)
from app.agent.tools.local.readiness import ReadinessCheckInput
from app.agent.tools.local.scoring import ScoreCalculateInput
from app.agent.tools.registry import ToolRegistry
from app.schemas.report import RawAIReport, UserReport
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.slots import CompanySlots, SlotValue


# ── 注册 ──

def test_register_local_tools_registers_expected_tools():
    r = ToolRegistry()
    register_local_tools(r)
    names = {t.name for t in r.list_all()}
    assert names == {
        "question_catalog.read",
        "readiness.check",
        "score.calculate",
        "report.split",
        "report.guard",
    }


def test_local_tools_are_read_only_and_concurrency_safe():
    r = ToolRegistry()
    register_local_tools(r)
    for t in r.list_all():
        assert t.is_read_only is True, f"{t.name} should be read_only"
        assert t.is_concurrency_safe is True, f"{t.name} should be concurrency_safe"
        assert t.is_destructive is False, f"{t.name} should not be destructive"
        assert t.max_retries == 0, f"{t.name} should have max_retries=0"


def test_register_local_tools_does_not_create_global_registry():
    r1 = ToolRegistry()
    r2 = ToolRegistry()
    register_local_tools(r1)
    register_local_tools(r2)
    assert len(r2.list_all()) == 5
    assert len(r1.list_all()) == 5
    r2.register(ToolDefinition(
        name="extra", description="e",
        input_model=QuestionCatalogInput,
        handler=lambda i, c: None,
    ))
    assert len(r2.list_all()) == 6
    assert len(r1.list_all()) == 5


# ── external 工具元数据 ──

def test_external_deepseek_tools_are_read_only_not_concurrency_safe():
    r = ToolRegistry()
    register_external_tools(r)
    for t in r.list_all():
        assert t.is_read_only is True, f"{t.name} should be read_only"
        assert t.is_concurrency_safe is False, f"{t.name} should NOT be concurrency_safe"


# ── question_catalog.read ──

@pytest.mark.asyncio
async def test_question_catalog_returns_questions():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("question_catalog.read", QuestionCatalogInput(branch=None))
    assert result.error is None
    assert len(result.data.questions) > 0


@pytest.mark.asyncio
async def test_question_catalog_filters_experienced_branch():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    all_result = await ex.execute("question_catalog.read", QuestionCatalogInput(branch=None))
    exp_result = await ex.execute("question_catalog.read", QuestionCatalogInput(branch="experienced"))
    inexp_result = await ex.execute("question_catalog.read", QuestionCatalogInput(branch="inexperienced"))

    # branch=None 返回全部 37 题
    # branch="experienced" 返回 common + branch_decision + experienced = 全部（无 inexperienced-only 题）
    # branch="inexperienced" 只返回 common + branch_decision，不包含 experienced 题
    assert len(exp_result.data.questions) == len(all_result.data.questions)
    assert len(inexp_result.data.questions) < len(exp_result.data.questions)
    ids = {q.id for q in exp_result.data.questions}
    assert "Q6" in ids  # experienced-only


@pytest.mark.asyncio
async def test_question_catalog_contains_dimension_names():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("question_catalog.read", QuestionCatalogInput(branch="experienced"))
    assert result.data.dimension_names == DIMENSION_NAMES
    assert result.data.key_question_ids == ["Q5", "Q8", "Q17", "Q19", "Q30", "Q31"]


@pytest.mark.asyncio
async def test_question_catalog_display_id_maps_subquestions():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("question_catalog.read", QuestionCatalogInput(branch=None))
    q_map = {q.id: q.display_id for q in result.data.questions}
    assert q_map.get("Q2a") == "Q2"
    assert q_map.get("Q2b") == "Q2"
    assert q_map.get("Q2c") == "Q2"
    assert q_map.get("Q3a") == "Q3"
    assert q_map.get("Q3b") == "Q3"
    assert q_map.get("Q3c") == "Q3"
    assert q_map.get("Q10a") == "Q10"
    assert q_map.get("Q10b") == "Q10"
    assert q_map.get("Q10c") == "Q10"
    assert q_map.get("Q5") == "Q5"
    assert q_map.get("Q1") == "Q1"


# ── readiness.check ──

@pytest.mark.asyncio
async def test_readiness_missing_q5_not_ready():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("readiness.check", ReadinessCheckInput(answers={}, branch=None))
    assert result.data.ready is False
    assert any(m.question_id == "Q5" for m in result.data.missing_items)


@pytest.mark.asyncio
async def test_readiness_branch_none_not_ready():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers={"Q4": ["A"]}, branch=None,
    ))
    assert result.data.ready is False
    assert result.data.unsupported_branch is False


@pytest.mark.asyncio
async def test_readiness_inexperienced_unsupported():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers={"Q5": ["D"]}, branch="inexperienced",
    ))
    assert result.data.ready is False
    assert result.data.unsupported_branch is True


@pytest.mark.asyncio
async def test_readiness_experienced_insufficient_answers_not_ready():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers={"Q5": ["A"]}, branch="experienced",
    ))
    assert result.data.ready is False
    assert len(result.data.missing_items) > 0


@pytest.mark.asyncio
async def test_readiness_experienced_enough_answers_ready():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    answers = {
        "Q5": ["A"], "Q6": ["A"], "Q8": ["A"], "Q11": ["A"],
        "Q17": ["A"], "Q19": ["A"], "Q22": ["A"], "Q30": ["A"],
        "Q31": ["A"],
    }
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers=answers, branch="experienced",
    ))
    assert result.data.ready is True


@pytest.mark.asyncio
async def test_readiness_missing_key_question_not_ready_even_with_enough_answers():
    """answers >= 8 但缺 Q19 → 仍应 ready=False。"""
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    answers = {
        "Q5": ["A"], "Q6": ["A"], "Q8": ["A"], "Q11": ["A"],
        "Q17": ["A"], "Q22": ["A"], "Q25": ["A"], "Q30": ["A"],
        "Q31": ["A"],
    }
    # 9 个 answers，但缺 Q19
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers=answers, branch="experienced",
    ))
    assert result.data.ready is False
    assert any(m.question_id == "Q19" for m in result.data.missing_items)


@pytest.mark.asyncio
async def test_readiness_missing_q31_not_ready():
    """answers >= 8 但缺 Q31 → 仍应 ready=False。"""
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    answers = {
        "Q5": ["A"], "Q6": ["A"], "Q8": ["A"], "Q11": ["A"],
        "Q17": ["A"], "Q19": ["A"], "Q22": ["A"], "Q30": ["A"],
    }
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers=answers, branch="experienced",
    ))
    assert result.data.ready is False
    assert any(m.question_id == "Q31" for m in result.data.missing_items)


@pytest.mark.asyncio
async def test_readiness_requires_key_questions_and_min_answer_count():
    """关键问题齐全但总 answers < 8 → ready=False。"""
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    # 只有 5 个关键问题（不含 Q5），加上 Q5 = 6 个，< 8
    answers = {
        "Q5": ["A"], "Q8": ["A"], "Q17": ["A"],
        "Q19": ["A"], "Q30": ["A"], "Q31": ["A"],
    }
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers=answers, branch="experienced",
    ))
    assert result.data.ready is False


@pytest.mark.asyncio
async def test_readiness_key_questions_answered_but_count_low_reports_answer_count_only():
    """关键题齐全但数量不足时，missing_items 只含 answer_count，不重复含已回答关键题。"""
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    answers = {
        "Q5": ["A"],
        "Q8": ["A"],
        "Q17": ["A"],
        "Q19": ["A"],
        "Q30": ["A"],
        "Q31": ["A"],
    }
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers=answers, branch="experienced",
    ))
    assert result.data.ready is False
    # 必须包含 answer_count
    assert any(m.question_id == "answer_count" for m in result.data.missing_items)
    # 不应包含已回答的关键题
    key_ids = {"Q8", "Q17", "Q19", "Q30", "Q31"}
    for m in result.data.missing_items:
        assert m.question_id not in key_ids, f"不应报告已回答的 {m.question_id}"
    # next_questions 包含对应 label
    assert any("补充" in q for q in result.data.next_questions)


@pytest.mark.asyncio
async def test_readiness_missing_key_and_count_low_reports_both():
    """缺 Q31 且数量不足 → missing_items 包含 Q31 和 answer_count。"""
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    answers = {
        "Q5": ["A"], "Q8": ["A"], "Q17": ["A"],
        "Q19": ["A"], "Q30": ["A"],
    }
    result = await ex.execute("readiness.check", ReadinessCheckInput(
        answers=answers, branch="experienced",
    ))
    assert result.data.ready is False
    assert any(m.question_id == "Q31" for m in result.data.missing_items)
    assert any(m.question_id == "answer_count" for m in result.data.missing_items)


# ── score.calculate ──

def _valid_experienced_answers():
    return {
        "Q2a": ["A"], "Q2b": ["A"], "Q2c": ["A"],
        "Q3a": ["A"], "Q3b": ["A"], "Q3c": ["A"],
        "Q4": ["A"],
        "Q5": ["A"],
        "Q6": ["A"], "Q7": ["A"], "Q8": ["A"], "Q9": ["A"],
        "Q10a": ["A"], "Q10b": ["A"], "Q10c": ["A"],
        "Q11": ["A"], "Q12": ["B"], "Q13": ["A"], "Q14": ["A"],
        "Q15": ["A"], "Q16": ["A"],
        "Q17": ["A"], "Q18": ["F"], "Q19": ["A"], "Q20": ["A"],
        "Q21": ["A"],
        "Q22": ["A"], "Q23": ["A"], "Q24": ["B"], "Q25": ["A"],
        "Q26": ["A", "B", "C"],
        "Q27": ["A"], "Q28": ["A"], "Q29": ["A"],
        "Q30": ["A"], "Q31": ["A"],
    }


@pytest.mark.asyncio
async def test_score_calculate_returns_scoring_result_for_valid_answers():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    inp = ScoreCalculateInput(
        answers=_valid_experienced_answers(),
        branch="experienced",
    )
    result = await ex.execute("score.calculate", inp)
    assert result.error is None
    sr = result.data.scoring_result
    assert sr.feasibility_score > 0
    assert sr.lead_score > 0
    assert sr.tag in ("观察准备型", "轻量试探型", "基础具备型", "优先布局型")


@pytest.mark.asyncio
async def test_score_calculate_rejects_inexperienced_branch():
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    inp = ScoreCalculateInput(answers={}, branch="inexperienced")
    result = await ex.execute("score.calculate", inp)
    assert result.error is not None
    assert result.error.code == ToolErrorCode.PERMANENT


@pytest.mark.asyncio
async def test_score_calculate_invalid_question_id_returns_permanent():
    """无效 question_id 应返回 PERMANENT error。"""
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    inp = ScoreCalculateInput(answers={"INVALID_Q": ["A"]}, branch="experienced")
    result = await ex.execute("score.calculate", inp)
    assert result.error is not None
    assert result.error.code == ToolErrorCode.PERMANENT


# ── report.split ──

def _fake_raw_report():
    return RawAIReport(
        summary_conclusion="summary",
        positioning_assessment="positioning",
        content_assessment="content",
        conversion_assessment="conversion",
        recommended_path="path",
        risk_reminder="risk",
        action_plan_30days=["Step 1", "Step 2", "Step 3", "Step 4"],
        consultant_guide="guide",
        sales_followup="sales followup text",
        consultant_notes="consultant notes text",
    )


def _fake_scoring_result():
    return ScoringResult(
        feasibility_score=60,
        lead_score=55,
        display_score=60,
        tag="基础具备型",
        tag_explanation="具备基础条件",
        preliminary_judgment="初步判断",
        dimension_scores=[
            DimensionScore(name="d1", raw_score=10, max_score=20, normalized_score=50),
        ],
        strengths=["优势1"],
        risks=["风险1"],
        lead_priority="P1-重点跟进",
    )


@pytest.mark.asyncio
async def test_report_split_returns_user_and_lead_reports():
    from app.agent.tools.local.report_tools import ReportSplitInput

    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    inp = ReportSplitInput(
        raw_report=_fake_raw_report(),
        scoring_result=_fake_scoring_result(),
    )
    result = await ex.execute("report.split", inp)
    assert result.error is None
    assert result.data.user_report.tag == "基础具备型"
    assert result.data.user_report.feasibility_score == 60
    assert result.data.lead_report.lead_score == 55
    dump = result.data.user_report.model_dump()
    assert "lead_score" not in dump
    assert "sales_followup" not in dump


@pytest.mark.asyncio
async def test_report_split_uses_existing_splitter_fields():
    """slots 字段应正确流入 lead_report（复用 splitter 逻辑）。"""
    from app.agent.tools.local.report_tools import ReportSplitInput

    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    slots = CompanySlots(
        company_name=SlotValue(value="测试企业", confidence=0.9),
        industry=SlotValue(value="机械设备", confidence=0.9),
        main_product=SlotValue(value="数控机床", confidence=0.9),
        target_market=SlotValue(value="北美", confidence=0.9),
    )

    inp = ReportSplitInput(
        raw_report=_fake_raw_report(),
        scoring_result=_fake_scoring_result(),
        slots=slots,
    )
    result = await ex.execute("report.split", inp)
    assert result.error is None
    lr = result.data.lead_report
    assert lr.company_name == "测试企业"
    assert lr.industry == "机械设备"
    assert lr.product == "数控机床"
    assert lr.target_market == "北美"
    # recommended_next_action 来自 action_plan_30days[0]
    assert lr.recommended_next_action == "Step 1"


# ── report.guard ──

def _safe_user_report():
    return UserReport(
        feasibility_score=50,
        display_score=50,
        tag="轻量试探型",
        tag_explanation="较轻",
        preliminary_judgment="初步",
        strengths=["强"],
        risks=["弱"],
        summary_conclusion="总结",
        positioning_assessment="定位",
        content_assessment="内容",
        conversion_assessment="转化",
        dimension_scores=[],
        recommended_path="路径",
        risk_reminder="风险",
        action_plan_30days=["A", "B", "C", "D"],
        consultant_guide="引导",
    )


@pytest.mark.asyncio
async def test_report_guard_passes_safe_user_report():
    from app.agent.tools.local.report_tools import ReportGuardInput

    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    inp = ReportGuardInput(user_report=_safe_user_report())
    result = await ex.execute("report.guard", inp)
    assert result.error is None
    assert result.data.passed is True


@pytest.mark.asyncio
async def test_report_guard_rejects_forbidden_user_report():
    from app.agent.tools.local.report_tools import ReportGuardInput

    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)

    bad = _safe_user_report().model_copy(update={"summary_conclusion": "这里是 lead_score 相关信息"})
    inp = ReportGuardInput(user_report=bad)
    result = await ex.execute("report.guard", inp)
    assert result.error is not None
    assert result.error.code == ToolErrorCode.PERMANENT
