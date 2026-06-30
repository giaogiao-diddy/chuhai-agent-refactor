from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.anonymous import ANONYMOUS_USER_ID_ERROR, ANONYMOUS_USER_ID_PATTERN
from app.schemas.report_history import ReportDetailResponse, ReportListItem
from app.services.report_repository import (
    get_user_report_detail,
    get_user_report_detail_by_user_id,
    list_user_reports,
    list_user_reports_by_user_id,
)
from config import get_settings

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    anonymous_user_id: str | None = Query(
        None,
        min_length=8,
        max_length=100,
        pattern=ANONYMOUS_USER_ID_PATTERN,
        description=ANONYMOUS_USER_ID_ERROR,
    ),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user is not None:
        return await list_user_reports_by_user_id(db, user_id=current_user.id, limit=limit)
    return await list_user_reports(db, anonymous_user_id=anonymous_user_id, limit=limit)


@router.get("/{assessment_id}", response_model=ReportDetailResponse)
async def get_report(
    assessment_id: UUID,
    anonymous_user_id: str | None = Query(
        None,
        min_length=8,
        max_length=100,
        pattern=ANONYMOUS_USER_ID_PATTERN,
        description=ANONYMOUS_USER_ID_ERROR,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user is not None:
        detail = await get_user_report_detail_by_user_id(db, assessment_id, user_id=current_user.id)
    else:
        detail = await get_user_report_detail(db, assessment_id, anonymous_user_id=anonymous_user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    detail.wechat_qr_url = get_settings().WECHAT_QR_URL or None
    return detail
