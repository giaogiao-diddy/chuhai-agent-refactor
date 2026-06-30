SYSTEM_DIALOGUE = """你是深度未来的企业出海诊断顾问。
你的任务是与企业主对话，收集出海诊断所需的关键信息。
每次回复不超过 100 字。

你需要围绕以下关键信息提问（每轮最多 1-2 个问题）：
- 行业和主营产品
- 企业规模（成立年限、团队人数、营收）
- 海外订单占比和海外客户来源
- 目标市场和选择原因
- 产品优势、认证和交付能力
- 出海方式偏好和预算
- 新媒体和短视频经验
- 外贸团队和承接能力
- 咨询意向

规则：
- 用户已回答的信息不要重复问。
- 不要闲聊，紧扣出海诊断主题。
- 不要在单轮抛出长问卷。
- 在关键题库信息收集完成前，不要直接给广告投放方案、预算分配方案、KOC/KOL执行方案或平台运营细节。
- 先完成信息采集，再做诊断；如果用户要求具体建议，也要先追问当前缺失的题库信息。
- 语气专业、友好、简洁。"""

OPENING_MESSAGE = "你好，我是深度未来的企业出海诊断顾问。先从最关键的开始：你们主要做什么产品？目前有没有海外客户或外贸经验？"


KEY_QUESTION_HINTS = [
    ("Q1", "行业和主营产品"),
    ("Q2a", "成立年限"),
    ("Q2b", "团队人数"),
    ("Q3a", "年营收"),
    ("Q5", "海外订单占比"),
    ("Q8", "目标市场"),
    ("Q11", "产品优势"),
    ("Q19", "试错预算"),
    ("Q30", "咨询意向"),
]


def build_dialogue_system_prompt(state) -> str:
    collected = sorted(state.answers.keys())
    missing: list[str] = []
    for question_id, label in KEY_QUESTION_HINTS:
        if question_id == "Q1":
            has_q1 = bool(state.slots.industry and state.slots.main_product)
            if not has_q1:
                missing.append(f"{question_id} {label}")
            continue
        if question_id not in state.answers:
            missing.append(f"{question_id} {label}")

    collected_text = ", ".join(collected) if collected else "暂无"
    missing_text = "；".join(missing[:3]) if missing else "关键题已基本覆盖"
    return (
        f"{SYSTEM_DIALOGUE}\n\n"
        f"当前已收集题号: {collected_text}\n"
        f"下一轮优先补齐: {missing_text}\n"
        "请优先围绕上述缺口追问，最多问 1-2 个问题。"
    )
