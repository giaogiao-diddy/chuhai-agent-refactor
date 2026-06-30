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


REPORT_KEY_QUESTION_HINTS = [
    {"id": "Q1", "label": "行业和主营产品", "ask": "你们属于哪个行业，主推产品是什么？"},
    {"id": "Q2a", "label": "成立年限", "ask": "公司成立多久了？"},
    {"id": "Q2b", "label": "团队人数", "ask": "目前公司大概多少人？"},
    {"id": "Q3a", "label": "年营收", "ask": "去年大概年营收区间是多少？"},
    {"id": "Q5", "label": "海外订单占比", "ask": "目前海外订单或海外客户占比大概多少？"},
    {"id": "Q8", "label": "目标市场", "ask": "接下来最想重点做哪个海外市场？"},
    {"id": "Q11", "label": "产品优势", "ask": "你们产品相对同行最明显的优势是什么？"},
    {"id": "Q15", "label": "交付稳定性", "ask": "目前交付稳定吗？产能、交期是否可控？"},
    {"id": "Q19", "label": "试错预算", "ask": "每月能接受多少出海试错预算？"},
    {"id": "Q22", "label": "新媒体团队", "ask": "现在有没有负责新媒体或短视频的人？"},
    {"id": "Q23", "label": "海外社媒经验", "ask": "是否做过海外社媒或短视频账号？"},
    {"id": "Q28", "label": "外贸团队", "ask": "目前外贸团队有几个人？"},
    {"id": "Q30", "label": "咨询意向", "ask": "最想让出海顾问帮你解决什么问题？"},
    {"id": "Q31", "label": "预约意愿", "ask": "如果报告显示适合出海，是否愿意预约 1V1 咨询？"},
]


def get_missing_report_question_hints(state) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for item in REPORT_KEY_QUESTION_HINTS:
        question_id = item["id"]
        if question_id == "Q1":
            has_q1 = bool(state.slots.industry and state.slots.main_product)
            if not has_q1:
                missing.append(item)
            continue
        if question_id not in state.answers:
            missing.append(item)
    return missing


def build_dialogue_system_prompt(state) -> str:
    collected = sorted(state.answers.keys())
    missing = get_missing_report_question_hints(state)

    collected_text = ", ".join(collected) if collected else "暂无"
    missing_text = (
        "；".join(f"{item['id']} {item['label']}: {item['ask']}" for item in missing[:3])
        if missing else "关键题已基本覆盖"
    )
    intake_rule = (
        "报告生成关键问题尚未收集完整。下一轮必须优先追问上述缺失项，"
        "不要继续给平台投放、预算分配或运营执行建议。"
        if missing else "关键题已基本覆盖，可以围绕诊断结论做少量解释。"
    )
    return (
        f"{SYSTEM_DIALOGUE}\n\n"
        f"当前已收集题号: {collected_text}\n"
        f"下一轮优先补齐: {missing_text}\n"
        f"{intake_rule}\n"
        "请优先围绕上述缺口追问，最多问 1-2 个问题。"
    )
