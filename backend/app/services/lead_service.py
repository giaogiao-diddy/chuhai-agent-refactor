from __future__ import annotations
"""留资 + 报告解锁服务"""


async def create_lead(user_id: int, assessment_id: int, name: str, contact: str, company: str, role: str) -> dict:
    """保存留资信息并解锁对应测评的完整报告"""
    # TODO: 校验必填字段 → 写入 leads 表 → 解锁 reports.is_unlocked
    raise NotImplementedError
