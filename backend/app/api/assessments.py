from __future__ import annotations
"""测评相关接口"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.question import Question, QuestionOption
from app.models.report import Report
from app.schemas.assessment import (
    AnswerSubmit,
    AssessmentCreateResponse,
    CompleteResponse,
    ReportStatusResponse,
)
from app.services.scoring_service import calculate_score_and_tag
from config import settings

router = APIRouter(tags=["assessments"])


@router.post("/assessments", response_model=AssessmentCreateResponse)
def create_assessment(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建新测评"""
    assessment = Assessment(user_id=current_user["user_id"], status="in_progress")
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return AssessmentCreateResponse(id=assessment.id, status=assessment.status)


@router.post("/assessments/{assessment_id}/answers")
def submit_answer(
    assessment_id: int,
    body: AnswerSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """提交单题答案 — 重复提交同一题自动覆盖"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作此测评")
    if assessment.status != "in_progress":
        raise HTTPException(status_code=400, detail="测评已完成，不可继续答题")

    question = db.query(Question).filter_by(id=body.question_id, is_active=True).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    option = None
    answer_text = None
    score = 0
    if question.is_scored:
        if body.option_id is None:
            raise HTTPException(status_code=400, detail="请选择一个选项")
        option = db.query(QuestionOption).filter_by(
            id=body.option_id,
            question_id=body.question_id,
        ).first()
        if not option:
            raise HTTPException(status_code=400, detail="选项与题目不匹配")
        score = option.score
    else:
        answer_text = (body.answer_text or "").strip()
        if not answer_text:
            raise HTTPException(status_code=400, detail="请输入行业信息")

    # upsert: 同一测评同一题反复提交 = 覆盖
    answer = (
        db.query(Answer)
        .filter_by(assessment_id=assessment_id, question_id=body.question_id)
        .first()
    )
    if answer:
        answer.option_id = option.id if option else None
        answer.answer_text = answer_text
        answer.score = score
    else:
        answer = Answer(
            assessment_id=assessment_id,
            question_id=body.question_id,
            option_id=option.id if option else None,
            answer_text=answer_text,
            score=score,
        )
        db.add(answer)
    db.commit()
    db.refresh(answer)
    if settings.ai_report_enabled and settings.llm_api_key:
        background_tasks.add_task(_diagnose_single_question_bg, assessment_id, body.question_id)
    return {
        "question_id": answer.question_id,
        "option_id": answer.option_id,
        "answer_text": answer.answer_text,
        "score": answer.score,
    }


@router.post("/assessments/{assessment_id}/complete", response_model=CompleteResponse)
def complete_assessment(
    assessment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """完成测评 — 校验 18 题完整性 → 算分打标签 → 后台生成报告"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作此测评")

    questions = db.query(Question).filter_by(is_active=True).order_by(Question.sort_order).all()
    answers = db.query(Answer).filter_by(assessment_id=assessment_id).all()
    answers_by_question = {answer.question_id: answer for answer in answers}
    missing_question_ids = []
    invalid_question_ids = []

    for question in questions:
        answer = answers_by_question.get(question.id)
        if not answer:
            missing_question_ids.append(question.id)
            continue
        if question.is_scored and not answer.option_id:
            invalid_question_ids.append(question.id)
        if not question.is_scored and not (answer.answer_text or "").strip():
            invalid_question_ids.append(question.id)

    if missing_question_ids or invalid_question_ids:
        raise HTTPException(
            status_code=400,
            detail=f"请完成全部 {len(questions)} 道题（当前已答 {len(answers_by_question)} 题）",
        )

    answer_dicts = [
        {"question_id": answer.question_id, "option_id": answer.option_id, "score": answer.score}
        for answer in answers
    ]
    score_result = calculate_score_and_tag(answer_dicts)

    assessment.total_score = score_result["raw_score"]
    assessment.tag = score_result["tag"]
    assessment.status = "generating"
    db.flush()

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if report:
        report.generation_status = "pending"
        report.generation_error = None
    else:
        report = Report(assessment_id=assessment_id, generation_status="pending")
        db.add(report)
    db.commit()
    db.refresh(assessment)

    # 后台异步生成报告
    background_tasks.add_task(_generate_report_bg, assessment_id)

    return CompleteResponse(
        assessment_id=assessment.id,
        total_score=assessment.total_score,
        display_score=score_result["display_score"],
        tag=assessment.tag,
        tag_explanation=score_result["tag_explanation"],
        status=assessment.status,
    )


@router.get("/assessments/{assessment_id}/report-status", response_model=ReportStatusResponse)
def get_report_status(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """轮询报告生成状态 — 需登录 + 归属校验"""
    import datetime
    assessment = db.query(Assessment).filter_by(
        id=assessment_id,
        user_id=current_user["user_id"],
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")

    report = db.query(Report).filter_by(assessment_id=assessment_id).first()
    if not report:
        return ReportStatusResponse(status="pending")

    elapsed = None
    if assessment.completed_at:
        elapsed = int((datetime.datetime.utcnow() - assessment.completed_at).total_seconds())

    return ReportStatusResponse(
        status=report.generation_status,
        generation_type=report.generation_type,
        has_summary=report.summary_report_json is not None,
        has_full=report.full_report_json is not None,
        elapsed_seconds=elapsed,
    )


# ── 后台任务 ──────────────────────────────────────────────────────

def _diagnose_single_question_bg(assessment_id: int, question_id: int):
    """后台静默生成单题诊断，异常不影响答题主流程。"""
    from app.core.database import SessionLocal
    from app.services.report_service import diagnose_single_question

    db = SessionLocal()
    try:
        diagnose_single_question(db, assessment_id, question_id)
    except Exception as e:
        import logging
        logger = logging.getLogger("luobin")
        logger.info("后台单题诊断异常 assessment_id=%s question_id=%s: %s", assessment_id, question_id, e)
        db.rollback()
    finally:
        db.close()

def _generate_report_bg(assessment_id: int):
    """后台异步生成报告 — AI 失败走模板兜底，异常时回写 failed 状态"""
    from app.core.database import SessionLocal
    from app.services.report_service import generate_report
    from app.models.report import Report

    db = SessionLocal()
    try:
        generate_report(db, assessment_id)
    except Exception as e:
        import logging
        logger = logging.getLogger("luobin")
        logger.exception("后台报告生成异常 assessment_id=%s: %s", assessment_id, e)
        try:
            report = db.query(Report).filter_by(assessment_id=assessment_id).first()
            if report:
                report.generation_status = "failed"
                report.generation_error = str(e)[:512]
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
