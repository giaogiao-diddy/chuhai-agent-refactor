from __future__ import annotations
"""测评相关接口"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.assessment import Assessment
from app.models.answer import Answer
from app.models.question import QuestionOption
from app.models.report import Report
from app.schemas.assessment import (
    AnswerSubmit,
    AssessmentCreateResponse,
    CompleteResponse,
    ReportStatusResponse,
)
from app.services.scoring_service import calculate_total, score_to_tag

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

    option = db.query(QuestionOption).filter_by(id=body.option_id).first()
    if not option:
        raise HTTPException(status_code=400, detail="选项不存在")

    # upsert: 同一测评同一题反复提交 = 覆盖
    answer = (
        db.query(Answer)
        .filter_by(assessment_id=assessment_id, question_id=body.question_id)
        .first()
    )
    if answer:
        answer.option_id = body.option_id
        answer.score = option.score
    else:
        answer = Answer(
            assessment_id=assessment_id,
            question_id=body.question_id,
            option_id=body.option_id,
            score=option.score,
        )
        db.add(answer)
    db.commit()
    db.refresh(answer)
    return {"question_id": answer.question_id, "option_id": answer.option_id, "score": answer.score}


@router.post("/assessments/{assessment_id}/complete", response_model=CompleteResponse)
def complete_assessment(
    assessment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """完成测评 — 校验 15 题完整性 → 算分打标签 → 后台生成报告"""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="测评不存在")
    if assessment.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作此测评")

    answers = db.query(Answer).filter_by(assessment_id=assessment_id).all()
    if len(answers) < 15:
        raise HTTPException(status_code=400, detail=f"请完成全部 15 道题（当前已答 {len(answers)} 题）")

    answer_dicts = [{"question_id": a.question_id, "option_id": a.option_id, "score": a.score} for a in answers]
    raw_score = calculate_total(answer_dicts)
    tag, _ = score_to_tag(raw_score)

    assessment.total_score = raw_score
    assessment.tag = tag
    assessment.status = "generating"
    db.flush()

    # 创建 report 记录
    report = Report(assessment_id=assessment_id, generation_status="pending")
    db.add(report)
    db.commit()
    db.refresh(assessment)

    # 后台异步生成报告
    background_tasks.add_task(_generate_report_bg, assessment_id)

    return CompleteResponse(
        assessment_id=assessment.id,
        total_score=assessment.total_score,
        tag=assessment.tag,
        status=assessment.status,
    )


@router.get("/assessments/{assessment_id}/report-status", response_model=ReportStatusResponse)
def get_report_status(assessment_id: int, db: Session = Depends(get_db)):
    """轮询报告生成状态"""
    import datetime
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
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

def _generate_report_bg(assessment_id: int):
    """后台异步生成报告 — 独立 DB session，AI 失败走模板兜底"""
    from app.core.database import SessionLocal
    from app.services.report_service import generate_report

    db = SessionLocal()
    try:
        generate_report(db, assessment_id)
    finally:
        db.close()
