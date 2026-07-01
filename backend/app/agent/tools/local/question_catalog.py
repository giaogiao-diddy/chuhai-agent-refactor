from typing import Literal

from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolResult
from app.scoring.questionnaire import ALL_QUESTIONS

# 维度中文名映射（以 scoring-design.md 为准）
DIMENSION_NAMES: dict[str, str] = {
    "enterprise_base": "企业基本盘",
    "overseas_validation": "海外验证度",
    "product_supply_chain": "产品与供应链竞争力",
    "path_clarity": "出海路径清晰度",
    "content_fitness": "短视频获客适配度",
    "conversion_readiness": "销转承接能力",
    "action_readiness": "企业出海行动力",
}

# 报告关键问题（Phase 39.2 最小集合）
KEY_QUESTION_IDS = [
    "Q5",    # 海外订单占比（分流）
    "Q8",    # 目标市场
    "Q17",   # 出海方式
    "Q19",   # 试错预算
    "Q30",   # 最想解决的问题
    "Q31",   # 预约意愿
]


class QuestionCatalogItem(BaseModel):
    id: str
    display_id: str
    display_order: int
    sub_order: int
    text: str
    kind: str
    branch: str | None
    option_ids: list[str]


class QuestionCatalogInput(BaseModel):
    branch: Literal["experienced", "inexperienced"] | None = None


class QuestionCatalogOutput(BaseModel):
    questions: list[QuestionCatalogItem]
    dimension_names: dict[str, str]
    key_question_ids: list[str]


def question_catalog_handler(
    inp: QuestionCatalogInput,
    ctx: ToolContext,
) -> ToolResult:
    items: list[QuestionCatalogItem] = []
    for q in ALL_QUESTIONS:
        if inp.branch is not None and q.branch not in ("common", "branch_decision", inp.branch):
            continue
        items.append(QuestionCatalogItem(
            id=q.id,
            display_id=q.display_id,
            display_order=q.display_order,
            sub_order=q.sub_order,
            text=q.text,
            kind=q.kind,
            branch=q.branch,
            option_ids=[o.id for o in q.options],
        ))
    return ToolResult(data=QuestionCatalogOutput(
        questions=items,
        dimension_names=DIMENSION_NAMES,
        key_question_ids=KEY_QUESTION_IDS,
    ))
