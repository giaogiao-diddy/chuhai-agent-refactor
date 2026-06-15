from __future__ import annotations
"""AI 报告生成 + 模板兜底服务"""

import json
import logging
import datetime

from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.report import Report
from app.models.ai_report_log import AIReportLog
from app.services.scoring_service import score_to_tag
from app.services.template_report import build_summary, build_full
from config import settings

logger = logging.getLogger("luobin")


def parse_ai_response(data: dict | str | None) -> dict | None:
    """解析 AI 返回的响应，统一为 dict 或 None。"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, str) and data.strip():
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def validate_report_fields(data: dict) -> bool:
    """校验 AI 报告 JSON 的字段完整性。"""
    if not isinstance(data, dict):
        return False
    if "summary_report" not in data or "full_report" not in data:
        return False

    summary = data["summary_report"]
    full = data["full_report"]
    if not isinstance(summary, dict) or not isinstance(full, dict):
        return False

    if "preliminary_judgment" not in summary:
        return False
    if "strengths" not in summary or not isinstance(summary["strengths"], list):
        return False
    if "risks" not in summary or not isinstance(summary["risks"], list):
        return False
    if "summary_conclusion" not in full:
        return False
    if "dimension_scores" not in full or not isinstance(full["dimension_scores"], dict):
        return False
    if "action_plan_30days" not in full or not isinstance(full["action_plan_30days"], list):
        return False

    return True


def _build_answer_summary(answers: list) -> dict:
    """将答案列表转为 AI prompt 可用的摘要 dict"""
    return {
        f"q{a.question_id}_score": a.score
        for a in answers
    }


def _build_dimension_summary(answers: list) -> dict:
    """计算两个维度的得分摘要"""
    # 题目维度映射 (question_id → dimension)
    # 前 4 题是 company，后 11 题是 business
    company_scores = [a.score for a in answers if a.question_id <= 4]
    business_scores = [a.score for a in answers if a.question_id > 4]
    return {
        "company_total": sum(company_scores),
        "company_max": len(company_scores) * 4,
        "business_total": sum(business_scores),
        "business_max": len(business_scores) * 4,
    }


def generate_report(db: Session, assessment_id: int):
    """生成测评报告 — 先调 DeepSeek AI，失败则切模板兜底。

    Args:
        db: 数据库 session
        assessment_id: 测评 ID
    """
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        return

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report:
        return

    answers = db.query(Answer).filter_by(assessment_id=assessment_id).all()
    raw_score = assessment.total_score or calculate_total_from_answers(answers)
    tag = assessment.tag or score_to_tag(raw_score)[0]
    answer_summary = _build_answer_summary(answers)
    dimension_summary = _build_dimension_summary(answers)

    start_time = datetime.datetime.utcnow()
    report.generation_status = "generating"
    db.commit()

    ai_log = AIReportLog(
        assessment_id=assessment_id,
        model=settings.llm_model,
        prompt_version="v1.0",
        status="pending",
    )
    db.add(ai_log)
    db.commit()

    # ── 尝试 AI 路径 ──
    ai_success = False
    try:
        if not settings.llm_api_key:
            raise ValueError("AI 报告未启用（缺少 API Key）")

        from app.services.prompts import SYSTEM_FULL_REPORT

        prompt = SYSTEM_FULL_REPORT.format(
            total_score=raw_score,
            display_score=raw_score + 45,
            tag=tag,
            answers=str(answer_summary),
            dimension_summary=str(dimension_summary),
        )

        from openai import OpenAI
        client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=settings.llm_timeout,
        )
        raw_response = resp.choices[0].message.content or ""

        ai_log.raw_response = {"content": raw_response}
        parsed = parse_ai_response(raw_response)

        if parsed and validate_report_fields(parsed):
            report.summary_report_json = parsed["summary_report"]
            report.full_report_json = parsed["full_report"]
            report.generation_type = "ai"
            report.ai_model = settings.llm_model
            ai_log.parsed_response = parsed
            ai_log.status = "success"
            ai_success = True
        else:
            ai_log.status = "failed"
            ai_log.error_message = "JSON 校验失败或字段缺失"
    except Exception as e:
        logger.warning("AI 报告生成失败，切模板兜底: %s", str(e))
        ai_log.status = "failed"
        ai_log.error_message = str(e)[:512]

    # ── 模板兜底路径 ──
    if not ai_success:
        summary = build_summary(raw_score, tag, answer_summary)
        full = build_full(raw_score, tag, answer_summary)
        report.summary_report_json = summary
        report.full_report_json = full
        report.generation_type = "template"

    # ── 收尾 ──
    elapsed = int((datetime.datetime.utcnow() - start_time).total_seconds() * 1000)
    ai_log.latency_ms = elapsed
    report.generation_status = "success"
    assessment.status = "completed"
    assessment.completed_at = datetime.datetime.utcnow()
    db.commit()


def calculate_total_from_answers(answers: list) -> int:
    """从 Answer ORM 对象列表计算原始总分"""
    return sum(a.score for a in answers)
