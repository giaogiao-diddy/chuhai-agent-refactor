from pathlib import Path

from pydantic import BaseModel, Field

from app.schemas.agent_state import AgentMessage


class ConversationEvalCase(BaseModel):
    id: str
    title: str
    tags: list[str] = Field(default_factory=list)
    messages: list[AgentMessage]
    expected_answers: dict[str, list[str]]
    expected_score_ready: bool
    expected_report_ready: bool


class EvaluationPrediction(BaseModel):
    case_id: str
    answers: dict[str, list[str]]
    score_ready: bool
    report_ready: bool
    used_template_report: bool | None = None
    leaked_user_fields: bool | None = None


class EvaluationMetrics(BaseModel):
    total_cases: int
    key_answer_recall: float
    score_ready_accuracy: float
    report_ready_accuracy: float
    missing_info_false_positive_rate: float
    over_early_completion_rate: float
    template_fallback_rate: float | None = None
    field_leakage_rate: float | None = None


def load_eval_cases(path: Path) -> list[ConversationEvalCase]:
    return [ConversationEvalCase.model_validate(item) for item in _load_json(path)]


def evaluate_predictions(
    cases: list[ConversationEvalCase],
    predictions: list[EvaluationPrediction],
) -> EvaluationMetrics:
    pred_by_id = {p.case_id: p for p in predictions}
    matched_answers = 0
    expected_answer_count = 0
    score_ready_correct = 0
    report_ready_correct = 0
    score_ready_expected = 0
    missing_info_false_positive = 0
    report_not_ready_expected = 0
    over_early_completion = 0

    template_values: list[bool] = []
    leakage_values: list[bool] = []

    for case in cases:
        pred = pred_by_id[case.id]
        for qid, expected_options in case.expected_answers.items():
            expected_answer_count += 1
            actual_options = set(pred.answers.get(qid, []))
            if set(expected_options).issubset(actual_options):
                matched_answers += 1

        if pred.score_ready == case.expected_score_ready:
            score_ready_correct += 1
        if pred.report_ready == case.expected_report_ready:
            report_ready_correct += 1

        if case.expected_score_ready:
            score_ready_expected += 1
            if not pred.score_ready:
                missing_info_false_positive += 1

        if not case.expected_report_ready:
            report_not_ready_expected += 1
            if pred.report_ready:
                over_early_completion += 1

        if pred.used_template_report is not None:
            template_values.append(pred.used_template_report)
        if pred.leaked_user_fields is not None:
            leakage_values.append(pred.leaked_user_fields)

    return EvaluationMetrics(
        total_cases=len(cases),
        key_answer_recall=_safe_div(matched_answers, expected_answer_count),
        score_ready_accuracy=_safe_div(score_ready_correct, len(cases)),
        report_ready_accuracy=_safe_div(report_ready_correct, len(cases)),
        missing_info_false_positive_rate=_safe_div(
            missing_info_false_positive,
            score_ready_expected,
        ),
        over_early_completion_rate=_safe_div(
            over_early_completion,
            report_not_ready_expected,
        ),
        template_fallback_rate=(
            _safe_div(sum(1 for v in template_values if v), len(template_values))
            if template_values else None
        ),
        field_leakage_rate=(
            _safe_div(sum(1 for v in leakage_values if v), len(leakage_values))
            if leakage_values else None
        ),
    )


def _safe_div(a: int, b: int) -> float:
    return 0.0 if b == 0 else a / b


def _load_json(path: Path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))

