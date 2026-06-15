from __future__ import annotations
"""报告查询接口"""

from fastapi import APIRouter

from app.schemas.report import SummaryReport, FullReport

router = APIRouter(tags=["reports"])


@router.get("/reports/{assessment_id}/summary", response_model=SummaryReport)
async def get_summary_report(assessment_id: int):
    """获取部分报告（无需留资）"""
    raise NotImplementedError


@router.get("/reports/{assessment_id}/full", response_model=FullReport)
async def get_full_report(assessment_id: int):
    """获取完整报告 — 需先留资解锁，否则返回 403"""
    raise NotImplementedError
