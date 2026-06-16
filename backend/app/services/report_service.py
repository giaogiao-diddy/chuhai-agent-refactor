from __future__ import annotations
"""AI 报告生成 + 模板兜底服务"""

import datetime
import json
import logging

from sqlalchemy.orm import Session

from app.models.ai_report_log import AIReportLog
from app.models.answer import Answer
from app.models.assessment import Assessment
from app.models.question import Question, QuestionOption
from app.models.report import Report
from app.services.prompts import SYSTEM_DIAGNOSE_SINGLE_QUESTION, SYSTEM_GENERATE_FULL_REPORT
from app.services.scoring_service import calculate_total, score_to_tag
from app.services.template_report import build_full, build_summary
from config import settings

logger = logging.getLogger("luobin")


_DIMENSION_QUESTION_IDS = {
    "enterprise_capacity": {2, 3, 4},
    "overseas_foundation": {5, 6, 13, 14, 15, 16, 18},
    "product_trust_asset": {7, 8, 9, 17},
    "content_acquisition": {10, 11},
    "conversion_system": {12},
}


def parse_ai_response(data: dict | str | None) -> dict | None:
    """解析 AI 返回的响应，统一为 dict 或 None。"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, str) and data.strip():
        text = data.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _is_nonempty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_report_fields(data: dict) -> bool:
    """校验 V2 AI 报告 JSON 的字段完整性。"""
    if not isinstance(data, dict):
        return False
    if "summary_report" not in data or "full_report" not in data or "sales_followup" not in data:
        return False

    summary = data["summary_report"]
    full = data["full_report"]
    sales = data["sales_followup"]
    if not isinstance(summary, dict) or not isinstance(full, dict) or not isinstance(sales, dict):
        return False

    summary_string_fields = [
        "tag",
        "tag_explanation",
        "preliminary_judgment",
        "positioning_assessment",
        "content_assessment",
        "conversion_assessment",
        "unlock_hint",
    ]
    full_string_fields = [
        "summary_conclusion",
        "positioning_assessment",
        "content_assessment",
        "conversion_assessment",
        "recommended_path",
        "risk_reminder",
        "consultant_guide",
    ]

    if not isinstance(summary.get("total_score"), int):
        return False
    if not isinstance(summary.get("display_score"), int):
        return False
    if any(not _is_nonempty_string(summary.get(field)) for field in summary_string_fields):
        return False
    if "strengths" not in summary or not isinstance(summary["strengths"], list):
        return False
    if "risks" not in summary or not isinstance(summary["risks"], list):
        return False

    if any(not _is_nonempty_string(full.get(field)) for field in full_string_fields):
        return False
    if "dimension_scores" not in full or not isinstance(full["dimension_scores"], dict):
        return False
    if "action_plan_30days" not in full or not isinstance(full["action_plan_30days"], list):
        return False
    if "followup_focus" in sales and not isinstance(sales["followup_focus"], list):
        return False

    return True


def _answer_to_summary_item(db: Session, answer: Answer) -> dict:
    question = db.query(Question).filter_by(id=answer.question_id).first()
    option = None
    if answer.option_id:
        option = db.query(QuestionOption).filter_by(id=answer.option_id).first()

    selected_text = answer.answer_text or (option.option_text if option else "")
    return {
        "question_id": answer.question_id,
        "question_text": question.title if question else "",
        "dimension": question.dimension if question else "",
        "is_scored": bool(question.is_scored) if question else answer.score > 0,
        "option_id": answer.option_id,
        "answer_text": selected_text,
        "score": answer.score,
    }


def _build_answer_summary(db: Session, answers: list[Answer]) -> list[dict]:
    """将答案列表转为 AI prompt 可用的明细数组。"""
    return [
        _answer_to_summary_item(db, answer)
        for answer in sorted(answers, key=lambda item: item.question_id)
    ]


def _build_dimension_summary(answer_summary: list[dict]) -> dict:
    """计算 V2 五个能力维度的得分摘要。"""
    result = {}
    for dimension, question_ids in _DIMENSION_QUESTION_IDS.items():
        scores = [
            item["score"]
            for item in answer_summary
            if item["question_id"] in question_ids and item["score"] > 0
        ]
        result[dimension] = {
            "score": sum(scores),
            "max_score": len(question_ids) * 4,
            "answered_count": len(scores),
        }
    return result


def _call_llm(prompt: str) -> str:
    if not settings.ai_report_enabled or not settings.llm_api_key:
        raise ValueError("AI 报告未启用或缺少 API Key")

    from openai import OpenAI

    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=3500,
        timeout=settings.llm_timeout,
    )
    return resp.choices[0].message.content or ""


def _render_prompt(template: str, values: dict[str, object]) -> str:
    """只替换显式占位符，避免 Prompt 内 JSON 示例的大括号触发 format 解析。"""
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def diagnose_single_question(db: Session, assessment_id: int, question_id: int):
    """静默生成单题 AI 诊断记忆。失败只记录日志，不影响答题主流程。"""
    start_time = datetime.datetime.utcnow()
    ai_log = AIReportLog(
        assessment_id=assessment_id,
        question_id=question_id,
        model=settings.llm_model,
        prompt_version="v2.0-single-question",
        status="pending",
    )
    db.add(ai_log)
    db.commit()

    try:
        assessment = db.query(Assessment).filter_by(id=assessment_id).first()
        question = db.query(Question).filter_by(id=question_id).first()
        answer = db.query(Answer).filter_by(
            assessment_id=assessment_id,
            question_id=question_id,
        ).first()
        if not assessment or not question or not answer:
            raise ValueError("测评、题目或答案不存在")

        answers = db.query(Answer).filter_by(assessment_id=assessment_id).all()
        answer_summary = _build_answer_summary(db, answers)
        current = _answer_to_summary_item(db, answer)
        previous_summary = [
            item
            for item in answer_summary
            if item["question_id"] != question_id
        ]
        prompt = _render_prompt(SYSTEM_DIAGNOSE_SINGLE_QUESTION, {
            "question_text": question.title,
            "question_dimension": question.dimension,
            "answer_text": current["answer_text"],
            "score": answer.score,
            "previous_answer_summary": json.dumps(previous_summary, ensure_ascii=False),
        })

        ai_log.request_payload = {
            "question_id": question_id,
            "question_text": question.title,
            "answer": current,
            "previous_answer_summary": previous_summary,
        }
        raw_response = _call_llm(prompt)
        parsed = parse_ai_response(raw_response)
        ai_log.raw_response = {"content": raw_response}

        if not isinstance(parsed, dict):
            raise ValueError("单题诊断 JSON 解析失败")
        diagnosis_tag = parsed.get("diagnosis_tag")
        report_memory = parsed.get("report_memory")
        sales_hint = parsed.get("sales_hint")
        if not isinstance(diagnosis_tag, list) or not _is_nonempty_string(report_memory):
            raise ValueError("单题诊断字段缺失")

        ai_log.parsed_response = parsed
        ai_log.diagnosis_tag = diagnosis_tag
        ai_log.report_memory = report_memory
        ai_log.sales_hint = sales_hint or ""
        ai_log.status = "success"
    except Exception as e:
        logger.info("单题 AI 诊断失败 assessment_id=%s question_id=%s: %s", assessment_id, question_id, e)
        ai_log.status = "failed"
        ai_log.error_message = str(e)[:512]
    finally:
        elapsed = int((datetime.datetime.utcnow() - start_time).total_seconds() * 1000)
        ai_log.latency_ms = elapsed
        db.commit()


def _collect_report_memories(db: Session, assessment_id: int) -> list[dict]:
    logs = (
        db.query(AIReportLog)
        .filter_by(assessment_id=assessment_id, status="success")
        .filter(AIReportLog.question_id.isnot(None))
        .order_by(AIReportLog.question_id)
        .all()
    )
    return [
        {
            "question_id": log.question_id,
            "diagnosis_tag": log.diagnosis_tag or [],
            "report_memory": log.report_memory or "",
            "sales_hint": log.sales_hint or "",
        }
        for log in logs
        if log.report_memory
    ]


def generate_report(db: Session, assessment_id: int):
    """生成 V2 测评报告：优先 AI 汇总，失败则模板兜底。"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        return

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report:
        return

    answers = db.query(Answer).filter_by(assessment_id=assessment_id).all()
    raw_score = assessment.total_score or calculate_total([
        {"question_id": answer.question_id, "score": answer.score}
        for answer in answers
    ])
    tag = assessment.tag or score_to_tag(raw_score)[0]
    tag_explanation = score_to_tag(raw_score)[1]
    display_score = raw_score + 43
    answer_summary = _build_answer_summary(db, answers)
    dimension_summary = _build_dimension_summary(answer_summary)
    report_memories = _collect_report_memories(db, assessment_id)

    start_time = datetime.datetime.utcnow()
    report.generation_status = "generating"
    db.commit()

    ai_log = AIReportLog(
        assessment_id=assessment_id,
        question_id=None,
        model=settings.llm_model,
        prompt_version="v2.0-full-report",
        status="pending",
        request_payload={
            "total_score": raw_score,
            "display_score": display_score,
            "tag": tag,
            "answers_json": answer_summary,
            "dimension_summary": dimension_summary,
            "report_memories": report_memories,
        },
    )
    db.add(ai_log)
    db.commit()

    ai_success = False
    try:
        prompt = _render_prompt(SYSTEM_GENERATE_FULL_REPORT, {
            "total_score": raw_score,
            "display_score": display_score,
            "tag": tag,
            "answers_json": json.dumps(answer_summary, ensure_ascii=False),
            "dimension_summary": json.dumps(dimension_summary, ensure_ascii=False),
            "report_memories": json.dumps(report_memories, ensure_ascii=False),
        })
        raw_response = _call_llm(prompt)
        parsed = parse_ai_response(raw_response)
        ai_log.raw_response = {"content": raw_response}

        if parsed and validate_report_fields(parsed):
            summary_report = parsed["summary_report"]
            summary_report["total_score"] = raw_score
            summary_report["display_score"] = display_score
            summary_report["tag"] = tag
            summary_report["tag_explanation"] = tag_explanation

            report.summary_report_json = summary_report
            report.full_report_json = parsed["full_report"]
            report.generation_type = "ai"
            report.ai_model = settings.llm_model
            report.prompt_version = "v2.0-full-report"
            ai_log.parsed_response = parsed
            ai_log.status = "success"
            ai_success = True
        else:
            raise ValueError("完整报告 JSON 校验失败或字段缺失")
    except Exception as e:
        logger.warning("AI 报告生成失败，切模板兜底: %s", str(e))
        ai_log.status = "failed"
        ai_log.error_message = str(e)[:512]

    if not ai_success:
        report.summary_report_json = build_summary(raw_score, tag, {"answers": answer_summary})
        report.full_report_json = build_full(raw_score, tag, {"answers": answer_summary})
        report.generation_type = "template"
        report.prompt_version = "v2.0-template"

    elapsed = int((datetime.datetime.utcnow() - start_time).total_seconds() * 1000)
    ai_log.latency_ms = elapsed
    report.generation_status = "success"
    report.generation_error = None
    assessment.status = "completed"
    assessment.completed_at = datetime.datetime.utcnow()
    db.commit()


def calculate_total_from_answers(answers: list[Answer]) -> int:
    """从 Answer ORM 对象列表计算原始总分。"""
    return calculate_total([
        {"question_id": answer.question_id, "score": answer.score}
        for answer in answers
    ])
