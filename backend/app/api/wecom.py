"""企业微信解锁接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.wecom import (
    WeComUnlockSessionCreate,
    WeComUnlockSessionResponse,
    WeComUnlockStatusResponse,
    WeComCustomerAddedRequest,
    MockUnlockRequest,
)
from app.services.wecom_unlock_service import (
    get_unlock_status,
    create_unlock_session,
    mark_wecom_added,
)
from config import settings

router = APIRouter(tags=["wecom"])


@router.post("/wecom/unlock-session", response_model=WeComUnlockSessionResponse)
def start_unlock_session(
    body: WeComUnlockSessionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建企微解锁会话 — 返回二维码和轮询配置"""
    result = create_unlock_session(
        db,
        user_id=current_user["user_id"],
        assessment_id=body.assessment_id,
    )
    return result


@router.get("/wecom/unlock-status/{assessment_id}", response_model=WeComUnlockStatusResponse)
def check_unlock_status(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """查询当前测评解锁状态 — 供前端轮询"""
    result = get_unlock_status(
        db,
        user_id=current_user["user_id"],
        assessment_id=assessment_id,
    )
    return result


@router.post("/wecom/customer-added")
def customer_added_callback(
    body: WeComCustomerAddedRequest,
    db: Session = Depends(get_db),
):
    """企业微信/SCRM 回调 — 确认客户已添加。

    生产环境需额外校验回调签名。当前版本先实现功能闭环。
    """
    result = mark_wecom_added(
        db,
        assessment_id=body.assessment_id,
        external_user_id=body.external_user_id,
        source=body.event,
    )
    return result


@router.post("/wecom/mock-unlock")
def mock_unlock(
    body: MockUnlockRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """开发环境模拟解锁 — 仅 enable_mock_wecom_unlock=True 时可用"""
    if not settings.enable_mock_wecom_unlock:
        raise HTTPException(status_code=403, detail="模拟解锁已关闭（生产环境不可用）")

    result = mark_wecom_added(
        db,
        assessment_id=body.assessment_id,
        user_id=current_user["user_id"],
        source="mock_unlock",
    )
    return result
