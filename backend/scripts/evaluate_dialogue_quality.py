# Run Agent dialogue extraction/readiness evaluation with real DeepSeek.
#
# Usage:
#   cd backend
#   python scripts/evaluate_dialogue_quality.py

import argparse
import asyncio
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agent.extraction import extract_from_messages
from app.agent.nodes import apply_extraction_result
from app.agent.tools.base import ToolContext
from app.agent.tools.local.readiness import ReadinessCheckInput, readiness_check_handler
from app.evaluation.conversation_quality import (
    EvaluationPrediction,
    evaluate_predictions,
    load_eval_cases,
)
from app.schemas.agent_state import AgentState


DEFAULT_CASES = BACKEND_ROOT / "evals" / "chuhai_dialogue_eval_cases.json"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Chuhai Agent extraction/readiness quality.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()

    cases = load_eval_cases(args.cases)
    if args.limit is not None:
        cases = cases[: args.limit]

    predictions: list[EvaluationPrediction] = []
    details: list[dict] = []

    for case in cases:
        state = AgentState(messages=case.messages)
        extraction = await extract_from_messages(case.messages, history_window=None)
        state = apply_extraction_result(state, extraction)
        readiness_result = readiness_check_handler(
            ReadinessCheckInput(answers=state.answers, branch=state.branch),
            ToolContext(),
        )
        readiness = readiness_result.data

        pred = EvaluationPrediction(
            case_id=case.id,
            answers=state.answers,
            score_ready=bool(getattr(readiness, "score_ready", readiness.ready)),
            report_ready=bool(getattr(readiness, "report_ready", readiness.ready)),
        )
        predictions.append(pred)
        details.append({
            "case_id": case.id,
            "title": case.title,
            "expected_answers": case.expected_answers,
            "predicted_answers": state.answers,
            "expected_score_ready": case.expected_score_ready,
            "predicted_score_ready": pred.score_ready,
            "expected_report_ready": case.expected_report_ready,
            "predicted_report_ready": pred.report_ready,
            "missing_items": [m.model_dump() for m in readiness.missing_items],
            "report_missing_items": [m.model_dump() for m in readiness.report_missing_items],
        })

    metrics = evaluate_predictions(cases, predictions)
    output = {"metrics": metrics.model_dump()}
    if args.details:
        output["details"] = details

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
