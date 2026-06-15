from __future__ import annotations
"""题库接口"""

from fastapi import APIRouter

from app.schemas.question import QuestionListResponse

router = APIRouter(tags=["questions"])


@router.get("/questions", response_model=QuestionListResponse)
async def get_questions():
    """获取全部 15 道题及选项"""
    # TODO: 从数据库查询活跃题目，按 sort_order 排序
    raise NotImplementedError
