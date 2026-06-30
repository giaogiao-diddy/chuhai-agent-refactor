from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_consultant_required
from app.db.session import get_db
from app.models import User
from app.schemas.admin_lead import AdminLeadDetail, AdminLeadFollowupUpdate, AdminLeadListItem, FollowupStatus
from app.services.admin_lead_repository import get_admin_lead_detail, list_admin_leads, update_lead_followup

router = APIRouter(prefix="/admin/leads", tags=["admin-leads"])


@router.get("", response_model=list[AdminLeadListItem])
async def list_leads(
    limit: int = Query(50, ge=1, le=100),
    followup_status: FollowupStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _consultant: User = Depends(get_current_consultant_required),
):
    return await list_admin_leads(db, limit=limit, followup_status=followup_status)


@router.get("/{submission_id}", response_model=AdminLeadDetail)
async def get_lead(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
    _consultant: User = Depends(get_current_consultant_required),
):
    detail = await get_admin_lead_detail(db, submission_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="线索不存在")
    return detail


@router.patch("/{submission_id}/followup", response_model=AdminLeadDetail)
async def patch_followup(
    submission_id: UUID,
    payload: AdminLeadFollowupUpdate,
    db: AsyncSession = Depends(get_db),
    _consultant: User = Depends(get_current_consultant_required),
):
    detail = await update_lead_followup(
        db, submission_id, payload.followup_status, payload.followup_note
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="线索不存在")
    return detail
