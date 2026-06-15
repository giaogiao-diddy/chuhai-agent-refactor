from __future__ import annotations
"""后台管理接口"""

from fastapi import APIRouter

from app.schemas.admin import (
    LeadFilter,
    LeadDetailResponse,
    AssessmentDetailResponse,
    AIReportLogResponse,
    FollowNoteCreate,
)

router = APIRouter(tags=["admin"])


@router.get("/admin/leads", response_model=list[LeadDetailResponse])
async def list_leads(page: int = 1, size: int = 20, tag: str | None = None, is_unlocked: bool | None = None):
    """后台线索列表 — 支持按标签、留资状态筛选"""
    raise NotImplementedError


@router.get("/admin/assessments/{assessment_id}", response_model=AssessmentDetailResponse)
async def get_assessment_detail(assessment_id: int):
    """后台测评详情 — 查看 15 题答案和报告"""
    raise NotImplementedError


@router.get("/admin/ai-report-logs", response_model=list[AIReportLogResponse])
async def list_ai_report_logs(page: int = 1, size: int = 20, status: str | None = None):
    """AI 调用日志列表"""
    raise NotImplementedError


@router.post("/admin/follow-notes")
async def create_follow_note(body: FollowNoteCreate):
    """创建跟进备注"""
    raise NotImplementedError
