from __future__ import annotations
"""测评相关接口"""

from fastapi import APIRouter

from app.schemas.assessment import (
    AnswerSubmit,
    AssessmentCreateResponse,
    AssessmentResponse,
    CompleteResponse,
    ReportStatusResponse,
)

router = APIRouter(tags=["assessments"])


@router.post("/assessments", response_model=AssessmentCreateResponse)
async def create_assessment():
    """创建新测评"""
    raise NotImplementedError


@router.post("/assessments/{assessment_id}/answers")
async def submit_answer(assessment_id: int, body: AnswerSubmit):
    """提交单题答案"""
    raise NotImplementedError


@router.post("/assessments/{assessment_id}/complete", response_model=CompleteResponse)
async def complete_assessment(assessment_id: int):
    """完成测评 — 触发评分 + AI 报告生成"""
    raise NotImplementedError


@router.get("/assessments/{assessment_id}/report-status", response_model=ReportStatusResponse)
async def get_report_status(assessment_id: int):
    """轮询报告生成状态"""
    raise NotImplementedError
