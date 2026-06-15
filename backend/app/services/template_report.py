from __future__ import annotations
"""模板报告拼装 — AI 报告失败的兜底方案

模板输入/输出结构与 AI 报告完全一致，前端不区分来源。
"""


def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板 + 答案变量生成部分报告"""
    # TODO: 实现四种标签的模板插值
    raise NotImplementedError


def build_full(total_score: int, tag: str, answer_summary: dict) -> dict:
    """基于标签模板 + 答案变量生成完整报告"""
    # TODO: 实现四种标签的完整模板插值
    raise NotImplementedError
