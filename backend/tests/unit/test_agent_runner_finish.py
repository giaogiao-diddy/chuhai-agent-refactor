import pytest

from app.agent.runner import run_agent_event
from app.agent.tools.base import ToolContext, ToolDefinition, ToolError, ToolErrorCode, ToolResult
from app.agent.tools.local.readiness import MissingItem, ReadinessCheckInput, ReadinessResult
from app.agent.tools.local.report_tools import ReportGuardInput, ReportSplitInput
from app.agent.tools.local.scoring import ScoreCalculateInput, ScoreCalculateOutput
from app.agent.tools.external.rag import RagSearchInput
from app.agent.tools.external.report_audit import ReportAuditInput
from app.agent.tools.external.report_generation import ReportGenerateInput
from app.agent.tools.registry import ToolRegistry
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState
from app.schemas.audit import ReportAuditResult
from app.schemas.report import RawAIReport, LeadReport, UserReport
from app.schemas.scoring import DimensionScore, ScoringResult


def _fake_scoring_result():
    return ScoringResult(
        feasibility_score=65, lead_score=55, display_score=65,
        tag="基础具备型", tag_explanation="较完善",
        preliminary_judgment="适合出海",
        dimension_scores=[DimensionScore(name="d", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["s"], risks=["r"], lead_priority="P1",
    )


def _fake_raw_report():
    return RawAIReport(
        summary_conclusion="s", positioning_assessment="p", content_assessment="c",
        conversion_assessment="v", recommended_path="r", risk_reminder="rr",
        action_plan_30days=["1","2","3","4"], consultant_guide="g",
        sales_followup="sf", consultant_notes="cn",
    )


def _fake_user_report():
    return UserReport(
        feasibility_score=65, display_score=65, tag="基础具备型", tag_explanation="较完善",
        preliminary_judgment="适合出海", strengths=["s"], risks=["r"],
        summary_conclusion="s", positioning_assessment="p",
        content_assessment="c", conversion_assessment="v",
        dimension_scores=[], recommended_path="r", risk_reminder="rr",
        action_plan_30days=["1","2","3","4"], consultant_guide="g",
    )


def _fake_lead_report():
    return LeadReport(
        lead_score=55, lead_priority="P1", tag="基础具备型",
        sales_followup="sf", consultant_notes="cn",
    )


# ── helpers ──

def _build_fake_finish_registry(**overrides) -> ToolRegistry:
    r = ToolRegistry()

    def _ready(inp, ctx):
        if inp.branch == "inexperienced":
            return ToolResult(data=ReadinessResult(ready=False, unsupported_branch=True))
        if "Q5" not in inp.answers:
            return ToolResult(data=ReadinessResult(ready=False, missing_items=[MissingItem(
                question_id="Q5", label="海外订单占比", reason="需要确认",
            )]))
        return ToolResult(data=ReadinessResult(ready=True))

    def _score(inp, ctx):
        if inp.branch == "inexperienced":
            return ToolResult(error=ToolError(code=ToolErrorCode.PERMANENT, message="x", retryable=False))
        return ToolResult(data=ScoreCalculateOutput(scoring_result=_fake_scoring_result()))

    def _default_split(inp, ctx):
        return ToolResult(data=type("X",(),{
            "user_report": _fake_user_report(),
            "lead_report": _fake_lead_report(),
        })())

    def _default_guard(inp, ctx):
        return ToolResult(data=type("X",(),{"passed": True})())

    r.register(ToolDefinition(name="readiness.check", description="r", input_model=ReadinessCheckInput, handler=overrides.get("readiness", _ready)))
    r.register(ToolDefinition(name="score.calculate", description="s", input_model=ScoreCalculateInput, handler=overrides.get("score", _score)))
    r.register(ToolDefinition(name="rag.search", description="rg", input_model=RagSearchInput, handler=overrides.get("rag", lambda i, c: ToolResult(data=type("X",(),{"matches":[]})()))))
    r.register(ToolDefinition(name="report.generate.deepseek", description="g", input_model=ReportGenerateInput, handler=overrides.get("generate", lambda i, c: ToolResult(data=type("X",(),{"raw_report":_fake_raw_report()})()))))
    r.register(ToolDefinition(name="report.audit.deepseek", description="a", input_model=ReportAuditInput, handler=overrides.get("audit", lambda i, c: ToolResult(data=type("X",(),{"audit_result":ReportAuditResult(passed=True, issues=[], rewrite_required=False, severity="pass")})()))))
    r.register(ToolDefinition(name="report.split", description="sp", input_model=ReportSplitInput, handler=overrides.get("split", _default_split)))
    r.register(ToolDefinition(name="report.guard", description="gd", input_model=ReportGuardInput, handler=overrides.get("guard", _default_guard)))
    # extract_answers.deepseek for recovery extraction in finish flow
    r.register(ToolDefinition(name="extract_answers.deepseek", description="ex", input_model=ExtractAnswersDeepSeekInput,
               handler=overrides.get("extract", lambda i, c: ToolResult(data=ExtractionResult()))))
    return r


def _ready_state():
    return AgentState(
        answers={"Q5":["A"],"Q6":["A"],"Q8":["A"],"Q11":["A"],"Q17":["A"],"Q19":["A"],"Q22":["A"],"Q30":["A"],"Q31":["A"]},
        branch="experienced",
    )


# ── tests ──

@pytest.mark.asyncio
async def test_finish_missing_info_no_score_no_report():
    state = AgentState(answers={}, branch=None)
    r = _build_fake_finish_registry()
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.MISSING_INFO
    assert result.state.scoring_result is None
    assert result.state.user_report is None
    assert result.state.used_template_report is False


@pytest.mark.asyncio
async def test_finish_unsupported_branch_no_score():
    state = AgentState(answers={"Q5": ["D"]}, branch="inexperienced")
    r = _build_fake_finish_registry()
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.UNSUPPORTED_BRANCH
    assert result.state.scoring_result is None
    assert result.state.user_report is None


@pytest.mark.asyncio
async def test_finish_ready_completes():
    r = _build_fake_finish_registry()
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert result.state.scoring_result is not None
    assert result.state.user_report is not None
    assert result.state.used_template_report is False


@pytest.mark.asyncio
async def test_finish_rag_failure_does_not_template():
    r = _build_fake_finish_registry(
        rag=lambda i, c: ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message="fail", retryable=True)),
    )
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert result.state.used_template_report is False


@pytest.mark.asyncio
async def test_finish_report_generate_failure_triggers_template():
    call_count = [0]
    def _fail_gen(inp, ctx):
        call_count[0] += 1
        return ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message="fail", retryable=True))

    r = _build_fake_finish_registry(generate=_fail_gen)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED_WITH_TEMPLATE
    assert result.state.used_template_report is True
    assert call_count[0] == 3


@pytest.mark.asyncio
async def test_finish_audit_fail_three_times_templates():
    def _fail_audit(inp, ctx):
        return ToolResult(data=type("X",(),{"audit_result":ReportAuditResult(
            passed=False, issues=["不够具体"], rewrite_required=True, severity="fail",
        )})())

    r = _build_fake_finish_registry(audit=_fail_audit)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED_WITH_TEMPLATE
    assert result.state.used_template_report is True
    assert result.state.report_retry_count == 3


@pytest.mark.asyncio
async def test_finish_audit_feedback_injected_next_generation():
    gen_inputs = []
    def _capture_gen(inp, ctx):
        gen_inputs.append(inp.audit_feedback.copy() if hasattr(inp, 'audit_feedback') else [])
        return ToolResult(data=type("X",(),{"raw_report":_fake_raw_report()})())

    audit_calls = [0]
    def _fail_first_audit(inp, ctx):
        audit_calls[0] += 1
        if audit_calls[0] == 1:
            return ToolResult(data=type("X",(),{"audit_result":ReportAuditResult(
                passed=False, issues=["内容不够具体"], rewrite_required=True, severity="fail",
            )})())
        return ToolResult(data=type("X",(),{"audit_result":ReportAuditResult(
            passed=True, issues=[], rewrite_required=False, severity="pass",
        )})())

    r = _build_fake_finish_registry(generate=_capture_gen, audit=_fail_first_audit)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert len(gen_inputs) >= 2
    assert any("内容不够具体" in str(inp) for inp in gen_inputs), f"audit feedback 应注入: {gen_inputs}"


# ── Tool Runtime 工具调用测试 ──

@pytest.mark.asyncio
async def test_finish_uses_report_split_tool():
    split_calls = [0]
    def _counting_split(inp, ctx):
        split_calls[0] += 1
        return ToolResult(data=type("X",(),{"user_report":_fake_user_report(),"lead_report":_fake_lead_report()})())

    r = _build_fake_finish_registry(split=_counting_split)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert split_calls[0] >= 1, f"report.split 应被调用至少 1 次，实际: {split_calls[0]}"


@pytest.mark.asyncio
async def test_finish_uses_report_guard_tool():
    guard_calls = [0]
    def _counting_guard(inp, ctx):
        guard_calls[0] += 1
        return ToolResult(data=type("X",(),{"passed": True})())

    r = _build_fake_finish_registry(guard=_counting_guard)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert guard_calls[0] >= 1, f"report.guard 应被调用至少 1 次，实际: {guard_calls[0]}"


@pytest.mark.asyncio
async def test_finish_report_guard_error_injects_feedback():
    """guard 错误信息应注入下一次 report.generate。"""
    gen_inputs = []
    def _capture_gen(inp, ctx):
        gen_inputs.append(inp.audit_feedback.copy() if hasattr(inp, 'audit_feedback') else [])
        return ToolResult(data=type("X",(),{"raw_report":_fake_raw_report()})())

    guard_calls = [0]
    def _guard_first_fail(inp, ctx):
        guard_calls[0] += 1
        if guard_calls[0] == 1:
            return ToolResult(error=ToolError(
                code=ToolErrorCode.PERMANENT,
                message="用户报告包含敏感字段",
                retryable=False,
            ))
        return ToolResult(data=type("X",(),{"passed": True})())

    r = _build_fake_finish_registry(generate=_capture_gen, guard=_guard_first_fail)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert any("用户报告包含敏感字段" in str(inp) for inp in gen_inputs), f"guard error 应注入: {gen_inputs}"


@pytest.mark.asyncio
async def test_finish_structured_output_error_injects_feedback():
    """STRUCTURED_OUTPUT_ERROR 的错误信息应注入下一轮。"""
    gen_inputs = []
    gen_calls = [0]
    def _struct_error_then_ok(inp, ctx):
        gen_calls[0] += 1
        gen_inputs.append(inp.audit_feedback.copy() if hasattr(inp, 'audit_feedback') else [])
        if gen_calls[0] == 1:
            return ToolResult(error=ToolError(
                code=ToolErrorCode.STRUCTURED_OUTPUT_ERROR,
                message="缺少 consultant_guide",
                retryable=True,
            ))
        return ToolResult(data=type("X",(),{"raw_report":_fake_raw_report()})())

    r = _build_fake_finish_registry(generate=_struct_error_then_ok)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert any("缺少 consultant_guide" in str(inp) for inp in gen_inputs), f"STRUCTURED_OUTPUT_ERROR 应注入: {gen_inputs}"


# ── 日志覆盖 (caplog) ──

@pytest.mark.asyncio
async def test_finish_logs_report_generate_error_before_template(caplog):
    caplog.set_level("WARNING")

    call_count = [0]
    def _fail_gen(inp, ctx):
        call_count[0] += 1
        return ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message="generate failed", retryable=True))

    r = _build_fake_finish_registry(generate=_fail_gen)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED_WITH_TEMPLATE
    assert any("report.generate.deepseek" in rec.message and "generate failed" in rec.message
               for rec in caplog.records), f"日志应包含 generate error, got: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_finish_logs_audit_rejection_before_retry(caplog):
    caplog.set_level("WARNING")

    gen_inputs = []
    def _capture_gen(inp, ctx):
        gen_inputs.append(inp.audit_feedback.copy() if hasattr(inp, 'audit_feedback') else [])
        return ToolResult(data=type("X",(),{"raw_report":_fake_raw_report()})())

    audit_calls = [0]
    def _fail_audit(inp, ctx):
        audit_calls[0] += 1
        return ToolResult(data=type("X",(),{"audit_result":ReportAuditResult(
            passed=False, issues=["不够具体"], rewrite_required=True, severity="fail",
        )})())

    r = _build_fake_finish_registry(generate=_capture_gen, audit=_fail_audit)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED_WITH_TEMPLATE
    assert any("report.audit rejected" in rec.message for rec in caplog.records), \
        f"日志应包含 audit rejected, got: {[r.message for r in caplog.records]}"


@pytest.mark.asyncio
async def test_finish_logs_rag_error_but_continues(caplog):
    caplog.set_level("WARNING")

    r = _build_fake_finish_registry(
        rag=lambda i, c: ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message="rag down", retryable=True)),
    )
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert any("rag.search failed" in rec.message for rec in caplog.records), \
        f"日志应包含 rag.search failed, got: {[r.message for r in caplog.records]}"


# ── finish recovery extraction ──

from app.agent.tools.external.extraction import ExtractAnswersDeepSeekInput
from app.schemas.extraction import ExtractedAnswer, ExtractionResult


@pytest.mark.asyncio
async def test_finish_not_ready_runs_recovery_extraction_once():
    """第一次 readiness not ready → recovery extraction → 第二次 ready → completed。"""
    extract_calls = [0]

    def _ready_first_missing(inp, ctx):
        if "Q17" not in inp.answers:
            missing = [MissingItem(question_id="Q17", label="出海方式", reason="需要", ask="考虑哪些出海方式？")]
            return ToolResult(data=ReadinessResult(ready=False, missing_items=missing, next_questions=["考虑哪些出海方式？"]))
        return ToolResult(data=ReadinessResult(ready=True))

    def _recover_extract(inp, ctx):
        extract_calls[0] += 1
        return ToolResult(data=ExtractionResult(answers=[
            ExtractedAnswer(question_id="Q17", option_ids=["F"], confidence=0.9),
        ]))

    r = _build_fake_finish_registry(readiness=_ready_first_missing, extract=_recover_extract)

    state = AgentState(answers={"Q5":["A"],"Q8":["A"],"Q19":["A"],"Q30":["A"],"Q31":["A"],"Q6":["A"],"Q11":["A"],"Q22":["A"]}, branch="experienced")
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert extract_calls[0] == 1


@pytest.mark.asyncio
async def test_finish_recovery_still_missing_returns_missing_info():
    """recovery extraction 后仍 missing → MISSING_INFO + structured response。"""
    missing_info = [MissingItem(question_id="Q17", label="出海方式", reason="需要", ask="考虑哪些出海方式？")]

    def _always_not_ready(inp, ctx):
        return ToolResult(data=ReadinessResult(ready=False, missing_items=missing_info, next_questions=["考虑哪些出海方式？"]))

    def _empty_extract(inp, ctx):
        return ToolResult(data=ExtractionResult())

    r = _build_fake_finish_registry(readiness=_always_not_ready, extract=_empty_extract)

    state = AgentState(answers={"Q5":["A"]}, branch="experienced")
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.MISSING_INFO
    assert result.response["missing_items"][0]["question_id"] == "Q17"
    assert "next_questions" in result.response


@pytest.mark.asyncio
async def test_finish_recovery_extraction_error_returns_missing_info():
    """recovery extraction 返回 error → 仍然 MISSING_INFO。"""
    missing_info = [MissingItem(question_id="Q8", label="目标市场", reason="需要", ask="重点开发哪个市场？")]

    def _not_ready(inp, ctx):
        return ToolResult(data=ReadinessResult(ready=False, missing_items=missing_info, next_questions=["重点开发哪个市场？"]))

    def _fail_extract(inp, ctx):
        return ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message="fail", retryable=True))

    r = _build_fake_finish_registry(readiness=_not_ready, extract=_fail_extract)

    state = AgentState(answers={"Q5":["A"]}, branch="experienced")
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.MISSING_INFO
    assert result.state.scoring_result is None


# ── dialogue prompt 禁止信息已齐 ──

from app.agent.tools.external.dialogue import _build_dialogue_prompt, DialogueDeepSeekInput
from app.schemas.agent_state import AgentMessage


def test_dialogue_prompt_forbids_completion_when_missing_items():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hi")],
        missing_items=[{"label": "目标市场", "question_id": "Q8", "ask": "重点开发哪个市场？"}],
    )
    prompt = _build_dialogue_prompt(inp)
    assert "不允许声明" in prompt or "不允许" in prompt
    assert "信息已齐" in prompt
    assert "已安排顾问" in prompt
    assert "重点开发哪个市场" in prompt


# ── recovery extraction uses full history ──

@pytest.mark.asyncio
async def test_finish_recovery_extraction_uses_full_history():
    """recovery extraction 传入 history_window=None。"""
    captured_window = None

    def _ready_first_missing(inp, ctx):
        if "Q17" not in inp.answers:
            missing = [MissingItem(question_id="Q17", label="出海方式", reason="需要", ask="问？")]
            return ToolResult(data=ReadinessResult(ready=False, missing_items=missing))
        return ToolResult(data=ReadinessResult(ready=True))

    def _recover_extract(inp, ctx):
        nonlocal captured_window
        captured_window = inp.history_window
        return ToolResult(data=ExtractionResult(answers=[
            ExtractedAnswer(question_id="Q17", option_ids=["F"], confidence=0.9),
        ]))

    r = _build_fake_finish_registry(readiness=_ready_first_missing, extract=_recover_extract)
    state = AgentState(answers={"Q5":["A"], "Q8":["A"], "Q19":["A"], "Q30":["A"], "Q31":["A"], "Q6":["A"], "Q11":["A"], "Q22":["A"]}, branch="experienced")
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert captured_window is None, f"history_window 应为 None, 实际: {captured_window}"


@pytest.mark.asyncio
async def test_finish_recovery_to_inexperienced_returns_unsupported_branch():
    """recovery extraction 后 readiness → unsupported_branch。"""
    def _ready_first_missing(inp, ctx):
        if inp.branch != "inexperienced":
            missing = [MissingItem(question_id="Q5", label="海外订单占比", reason="需要")]
            return ToolResult(data=ReadinessResult(ready=False, missing_items=missing))
        return ToolResult(data=ReadinessResult(ready=False, unsupported_branch=True))

    def _recover_extract(inp, ctx):
        return ToolResult(data=ExtractionResult(answers=[
            ExtractedAnswer(question_id="Q5", option_ids=["D"], confidence=0.9),
        ]))

    r = _build_fake_finish_registry(readiness=_ready_first_missing, extract=_recover_extract)
    state = AgentState(answers={}, branch=None)
    result = await run_agent_event(state, AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.UNSUPPORTED_BRANCH
    assert result.state.scoring_result is None


# ── ReadinessResult default lists ──

def test_readiness_result_default_lists_are_independent():
    from app.schemas.readiness import ReadinessResult, MissingItem
    a = ReadinessResult(ready=False)
    b = ReadinessResult(ready=False)
    a.missing_items.append(MissingItem(question_id="Q8", label="目标市场", reason="需要"))
    assert len(a.missing_items) == 1
    assert len(b.missing_items) == 0


@pytest.mark.asyncio
async def test_finish_length_exceeded_sets_next_escalated_without_message_matching():
    """LENGTH_EXCEEDED 应基于 ToolErrorCode 驱动 escalated，而非 message 字符串。"""
    gen_inputs = []
    gen_calls = [0]
    def _length_then_ok(inp, ctx):
        gen_calls[0] += 1
        gen_inputs.append((inp.escalated, inp.audit_feedback.copy() if hasattr(inp, 'audit_feedback') else []))
        if gen_calls[0] == 1:
            # message 不含 "length" 或 "max_token"
            return ToolResult(error=ToolError(
                code=ToolErrorCode.LENGTH_EXCEEDED,
                message="输出被截断",
                retryable=True,
            ))
        return ToolResult(data=type("X",(),{"raw_report":_fake_raw_report()})())

    r = _build_fake_finish_registry(generate=_length_then_ok)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED
    assert len(gen_inputs) >= 2
    # 第一次 escalated 应为 False
    assert gen_inputs[0][0] is False
    # 第二次 escalated 应为 True（由 ToolErrorCode 驱动）
    assert gen_inputs[1][0] is True, f"第二次应 escalated=True, 实际: {gen_inputs}"


@pytest.mark.asyncio
async def test_finish_length_exceeded_escalates_only_once():
    """连续两次 LENGTH_EXCEEDED → 只升级一次，第二次直接 template。"""
    gen_inputs = []
    gen_calls = [0]
    def _double_length(inp, ctx):
        gen_calls[0] += 1
        gen_inputs.append((gen_calls[0], inp.escalated))
        return ToolResult(error=ToolError(
            code=ToolErrorCode.LENGTH_EXCEEDED,
            message=f"截断 attempt {gen_calls[0]}",
            retryable=True,
        ))

    r = _build_fake_finish_registry(generate=_double_length)
    result = await run_agent_event(_ready_state(), AgentEvent(type="finish_requested"), r)
    assert result.terminal == TerminalState.COMPLETED_WITH_TEMPLATE
    # 第一次: escalated=False
    assert gen_inputs[0] == (1, False)
    # 第二次: escalated=True（唯一一次升级）
    assert gen_inputs[1] == (2, True)
    # 不应该有第三次（第二次 LENGTH_EXCEEDED 后 break → template）
    assert len(gen_inputs) == 2, f"预期 2 次调用，实际 {len(gen_inputs)}"
