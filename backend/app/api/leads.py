from __future__ import annotations
"""留资与转发接口"""

from fastapi import APIRouter

from app.schemas.lead import LeadCreate, LeadResponse
from app.schemas.admin import ShareRecordCreate, ShareRecordResponse

router = APIRouter(tags=["leads"])


@router.post("/leads", response_model=LeadResponse)
async def create_lead(body: LeadCreate):
    """提交留资信息，解锁完整报告"""
    raise NotImplementedError


@router.post("/share-records", response_model=ShareRecordResponse)
async def record_share(body: ShareRecordCreate):
    """记录转发行为，增加顾问解读分钟数"""
    raise NotImplementedError
