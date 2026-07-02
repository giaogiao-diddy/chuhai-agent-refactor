from pathlib import Path

from app.evaluation.conversation_quality import (
    EvaluationPrediction,
    ConversationEvalCase,
    evaluate_predictions,
    load_eval_cases,
)
from app.schemas.agent_state import AgentMessage


def _case(
    case_id: str,
    expected_answers: dict[str, list[str]],
    expected_score_ready: bool,
    expected_report_ready: bool,
) -> ConversationEvalCase:
    return ConversationEvalCase(
        id=case_id,
        title=f"case {case_id}",
        tags=["unit"],
        messages=[
            AgentMessage(role="user", content="我们有海外订单，想做东南亚市场。"),
        ],
        expected_answers=expected_answers,
        expected_score_ready=expected_score_ready,
        expected_report_ready=expected_report_ready,
    )


def test_evaluate_predictions_computes_resume_quality_metrics():
    cases = [
        _case(
            "ready-but-missed",
            {"Q5": ["B"], "Q8": ["B"], "Q17": ["F"]},
            expected_score_ready=True,
            expected_report_ready=False,
        ),
        _case(
            "not-ready-overdone",
            {"Q5": ["C"], "Q8": ["A"]},
            expected_score_ready=False,
            expected_report_ready=False,
        ),
    ]
    predictions = [
        EvaluationPrediction(
            case_id="ready-but-missed",
            answers={"Q5": ["B"], "Q8": ["B"], "Q17": ["F"]},
            score_ready=False,
            report_ready=False,
            used_template_report=True,
            leaked_user_fields=False,
        ),
        EvaluationPrediction(
            case_id="not-ready-overdone",
            answers={"Q5": ["D"], "Q8": ["A"]},
            score_ready=False,
            report_ready=True,
            used_template_report=False,
            leaked_user_fields=False,
        ),
    ]

    metrics = evaluate_predictions(cases, predictions)

    assert metrics.total_cases == 2
    assert metrics.key_answer_recall == 4 / 5
    assert metrics.score_ready_accuracy == 1 / 2
    assert metrics.report_ready_accuracy == 1 / 2
    assert metrics.missing_info_false_positive_rate == 1.0
    assert metrics.over_early_completion_rate == 1 / 2
    assert metrics.template_fallback_rate == 1 / 2
    assert metrics.field_leakage_rate == 0.0


def test_load_eval_cases_contains_twenty_dialogues():
    cases = load_eval_cases(Path("evals/chuhai_dialogue_eval_cases.json"))

    assert len(cases) == 20
    assert all(case.messages for case in cases)
    assert all(case.expected_answers for case in cases)
    assert any(case.expected_report_ready for case in cases)
    assert any(not case.expected_score_ready for case in cases)
