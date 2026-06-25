from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_history import ReportDetailResponse, ReportListItem
from app.services.report_repository import get_user_report_detail, list_user_reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await list_user_reports(db, limit)


@router.get("/{assessment_id}", response_model=ReportDetailResponse)
async def get_report(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    detail = await get_user_report_detail(db, assessment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return detail
