# 企业出海可行性评估 — 完整题库常量。
# Q1-Q4 文案参考 企业出海可行性评估智能体（内容选项）.md
# Q6-Q31 文案以 有出海经验题目.md 为准
# F/L 分值严格对齐 docs/scoring-design.md
# 题号以 scoring-design.md 为准（Q1-Q31）。

from app.schemas.questionnaire import Question, QuestionnaireBranch, QuestionOption

# ═══════════════════════════════════════════════════════════════
# 公用题目（Q1-Q4）：所有分支通用
# ═══════════════════════════════════════════════════════════════

Q1 = Question(
    id="Q1", text="你的企业属于哪个行业？主要卖什么产品或服务？",
    dimension="enterprise_base", kind="open_text", branch="common",
    options=[],
    max_feasibility_score=2, max_lead_score=3, is_scored=True,
    notes="信息完整度评分：industry + main_product 都有值 → F=2/L=3；只有一个 → F=1/L=1；都没有 → 0。不评价行业好坏，只评价信息是否完整。",
)

Q2a = Question(
    id="Q2a", text="你的企业成立多久？（成立年限）",
    dimension="enterprise_base", kind="single_choice", branch="common",
    options=[
        QuestionOption(id="A", text="成立10年以上", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="成立5-10年", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="成立3-5年", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="成立1-3年", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=2,
)

Q2b = Question(
    id="Q2b", text="目前团队规模是多少？",
    dimension="enterprise_base", kind="single_choice", branch="common",
    options=[
        QuestionOption(id="A", text="299人以上", feasibility_score=3, lead_score=3),
        QuestionOption(id="B", text="100-299人", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="21-99人", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="20人以下", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=3,
)

Q2c = Question(
    id="Q2c", text="销售团队人数？",
    dimension="enterprise_base", kind="single_choice", branch="common",
    options=[
        QuestionOption(id="A", text="20人以上", feasibility_score=2, lead_score=3),
        QuestionOption(id="B", text="5-20人", feasibility_score=1, lead_score=2),
        QuestionOption(id="C", text="1-5人", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="无", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=3,
)

Q3a = Question(
    id="Q3a", text="过去一年营业额大约多少？",
    dimension="enterprise_base", kind="single_choice", branch="common",
    options=[
        QuestionOption(id="A", text="1亿以上", feasibility_score=3, lead_score=3),
        QuestionOption(id="B", text="5000万-1亿", feasibility_score=2, lead_score=3),
        QuestionOption(id="C", text="1000-5000万", feasibility_score=2, lead_score=2),
        QuestionOption(id="D", text="500-1000万", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="500万以下", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=3,
)

Q3b = Question(
    id="Q3b", text="产品毛利率大概是多少？",
    dimension="enterprise_base", kind="single_choice", branch="common",
    options=[
        QuestionOption(id="A", text="40%以上", feasibility_score=2, lead_score=1),
        QuestionOption(id="B", text="25%-40%", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="15%-25%", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="10%-15%", feasibility_score=1, lead_score=0),
        QuestionOption(id="E", text="10%以下", feasibility_score=0, lead_score=0),
        QuestionOption(id="F", text="不清楚毛利率", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=1,
)

Q3c = Question(
    id="Q3c", text="当前增长压力（可多选）",
    dimension="enterprise_base", kind="multiple_choice", branch="common",
    options=[
        QuestionOption(id="A", text="国内增长乏力，希望扩展海外市场", feasibility_score=2, lead_score=2),
        QuestionOption(id="B", text="产品利润下降，需要找到高价值客户", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="已有海外询盘，但不知道怎么系统放大", feasibility_score=2, lead_score=2),
        QuestionOption(id="F", text="不清楚问题在哪里，只是想试试出海", feasibility_score=1, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=2,
    cap_note="多选取最高分，封顶 F:2 / L:2",
)

Q4 = Question(
    id="Q4", text="你的企业性质更接近哪一种？",
    dimension="enterprise_base", kind="single_choice", branch="common",
    options=[
        QuestionOption(id="A", text="源头工厂", feasibility_score=3, lead_score=3),
        QuestionOption(id="B", text="工贸一体", feasibility_score=3, lead_score=2),
        QuestionOption(id="C", text="外贸公司/贸易商", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="自有品牌方", feasibility_score=3, lead_score=3),
        QuestionOption(id="F", text="非标定制/项目制服务企业", feasibility_score=1, lead_score=1),
        QuestionOption(id="G", text="解决方案公司", feasibility_score=2, lead_score=2),
        QuestionOption(id="H", text="海外IP", feasibility_score=2, lead_score=1),
    ], max_feasibility_score=3, max_lead_score=3,
)

# ═══════════════════════════════════════════════════════════════
# 分流题 Q5
# ═══════════════════════════════════════════════════════════════

Q5 = Question(
    id="Q5", text="你的营业额中，海外订单占比多少？",
    dimension="overseas_validation", kind="single_choice", branch="branch_decision",
    options=[
        QuestionOption(id="A", text="有，海外订单占比30%以上", feasibility_score=5, lead_score=5, next_branch="experienced"),
        QuestionOption(id="B", text="有，海外订单占比10%-30%", feasibility_score=4, lead_score=4, next_branch="experienced"),
        QuestionOption(id="C", text="有少量海外订单或样品单", feasibility_score=2, lead_score=2, next_branch="experienced"),
        QuestionOption(id="D", text="完全没有海外业务", feasibility_score=0, lead_score=0, next_branch="inexperienced"),
    ], max_feasibility_score=5, max_lead_score=5,
    notes="A/B/C → experienced；D → inexperienced（题库尚未提供）",
    conflict_note="选 D 时 Q6-Q10 跳过。无出海经验题库待提供。",
)

# ═══════════════════════════════════════════════════════════════
# 有出海经验分支（Q6-Q31）
# 文案以 有出海经验题目.md 为准，F/L 以 scoring-design.md 为准
# ═══════════════════════════════════════════════════════════════

# ── 维度二：海外验证度（F:20 / L:15）──

Q6 = Question(
    id="Q6", text="你目前海外客户的来源有哪些？（多选）",
    dimension="overseas_validation", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="海外展会", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="阿里国际站/中国制造网/环球资源等B2B平台", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="老客户介绍", feasibility_score=3, lead_score=2),
        QuestionOption(id="D", text="海外代理/渠道商", feasibility_score=3, lead_score=2),
        QuestionOption(id="E", text="独立站/Google广告", feasibility_score=2, lead_score=1),
        QuestionOption(id="F", text="TikTok/Instagram/Facebook/YouTube等社媒", feasibility_score=2, lead_score=1),
        QuestionOption(id="G", text="LinkedIn开发", feasibility_score=1, lead_score=1),
        QuestionOption(id="H", text="外贸业务员主动开发", feasibility_score=1, lead_score=1),
    ], max_feasibility_score=3, max_lead_score=2,
    cap_note="多选累加，封顶 F:3 / L:2",
)

Q7 = Question(
    id="Q7", text="你的海外客户主要分布在哪些国家或地区？（多选）",
    dimension="overseas_validation", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="北美：美国、加拿大", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="欧洲：英国、德国、法国、意大利、西班牙等", feasibility_score=3, lead_score=2),
        QuestionOption(id="C", text="东南亚：越南、泰国、印尼、马来西亚、菲律宾等", feasibility_score=2, lead_score=2),
        QuestionOption(id="D", text="中东：沙特、阿联酋、卡塔尔、科威特等", feasibility_score=2, lead_score=2),
        QuestionOption(id="E", text="拉美：墨西哥、巴西、智利、哥伦比亚等", feasibility_score=1, lead_score=1),
        QuestionOption(id="F", text="非洲：尼日利亚、南非、肯尼亚、埃及等", feasibility_score=1, lead_score=0),
        QuestionOption(id="G", text="俄罗斯及独联体", feasibility_score=1, lead_score=0),
        QuestionOption(id="H", text="日韩", feasibility_score=2, lead_score=1),
        QuestionOption(id="I", text="澳洲/新西兰", feasibility_score=2, lead_score=1),
    ], max_feasibility_score=3, max_lead_score=2,
    cap_note="多选累加，封顶 F:3 / L:2",
)

Q8 = Question(
    id="Q8", text="你最想开发的市场是？",
    dimension="overseas_validation", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="欧美成熟市场", feasibility_score=1, lead_score=2),
        QuestionOption(id="B", text="东南亚、中东、拉美等新兴市场", feasibility_score=1, lead_score=2),
        QuestionOption(id="C", text="一带一路沿线国家", feasibility_score=0, lead_score=1),
        QuestionOption(id="D", text="华人市场", feasibility_score=0, lead_score=1),
        QuestionOption(id="E", text="全球同步推进", feasibility_score=0, lead_score=1),
    ], max_feasibility_score=1, max_lead_score=2,
    conflict_note="企业出海可行性评估智能体（内容选项）.md 中 Q8 合并了市场选择/原因/订单；有出海经验题目.md 和 scoring-design 已拆为 Q8/Q9/Q10",
)

Q9 = Question(
    id="Q9", text="选择该市场的原因？",
    dimension="overseas_validation", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="已有客户或询盘", feasibility_score=2, lead_score=2),
        QuestionOption(id="B", text="认为竞争可能没那么激烈", feasibility_score=1, lead_score=1),
        QuestionOption(id="C", text="物流或贸易往来方便", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="同行已经在做", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="不清楚，只是凭感觉", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=2,
)

Q10a = Question(
    id="Q10a", text="单笔海外订单金额（人民币）？",
    dimension="overseas_validation", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="40万元以上", feasibility_score=2, lead_score=2),
        QuestionOption(id="B", text="10万-40万元", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="3万-10万元", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="5000元-3万元", feasibility_score=0, lead_score=0),
        QuestionOption(id="E", text="5000元以下", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=2,
)

Q10b = Question(
    id="Q10b", text="客户复购情况？",
    dimension="overseas_validation", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="复购频率高，客户长期采购", feasibility_score=2, lead_score=1),
        QuestionOption(id="B", text="有复购，但周期较长", feasibility_score=1, lead_score=1),
        QuestionOption(id="C", text="偶尔复购", feasibility_score=1, lead_score=0),
        QuestionOption(id="D", text="基本一次性采购", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=1,
)

Q10c = Question(
    id="Q10c", text="你最主要的海外订单类型？",
    dimension="overseas_validation", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="大B客户，订单大、周期长", feasibility_score=2, lead_score=1),
        QuestionOption(id="B", text="中小B客户，订单中等、复购较好", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="小B客户，成交快但客单不高", feasibility_score=1, lead_score=0),
        QuestionOption(id="D", text="C端消费者，低客单走量", feasibility_score=0, lead_score=0),
        QuestionOption(id="E", text="不确定客户类型", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=1,
)

# ── 维度三：产品与供应链竞争力（F:15 / L:12）──

Q11 = Question(
    id="Q11", text="与同行相比，你的产品最核心的优势是什么？（多选）",
    dimension="product_supply_chain", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="源头工厂，价格优势", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="支持定制，交期快", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="研发设计能力强", feasibility_score=3, lead_score=2),
        QuestionOption(id="D", text="认证齐全，符合多国标准", feasibility_score=3, lead_score=2),
        QuestionOption(id="E", text="供应链整合能力强", feasibility_score=2, lead_score=1),
        QuestionOption(id="F", text="售后服务好", feasibility_score=1, lead_score=1),
        QuestionOption(id="G", text="品牌影响力强", feasibility_score=3, lead_score=2),
    ], max_feasibility_score=3, max_lead_score=2, cap_note="多选累加，封顶 F:3 / L:2",
)

Q12 = Question(
    id="Q12", text="你认为海外客户最在意什么？",
    dimension="product_supply_chain", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="价格", feasibility_score=0, lead_score=0),
        QuestionOption(id="B", text="质量", feasibility_score=1, lead_score=1),
        QuestionOption(id="C", text="认证/合规", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="定制能力/交期", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="供应稳定性", feasibility_score=1, lead_score=1),
        QuestionOption(id="F", text="售后保障", feasibility_score=1, lead_score=0),
        QuestionOption(id="G", text="利润空间", feasibility_score=0, lead_score=0),
        QuestionOption(id="H", text="品牌背书", feasibility_score=1, lead_score=1),
        QuestionOption(id="I", text="不清楚", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=1, max_lead_score=1,
)

Q13 = Question(
    id="Q13", text="你的产品是否具备出口资质、认证、检测或合规基础？",
    dimension="product_supply_chain", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="出口资质、认证、检测报告、英文资料都比较完整", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="有部分认证或检测报告", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="可以出口，但资料不完整", feasibility_score=1, lead_score=0),
        QuestionOption(id="D", text="不清楚目标市场需要什么认证", feasibility_score=0, lead_score=0),
        QuestionOption(id="E", text="产品可能存在合规风险", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=2,
)

Q14 = Question(
    id="Q14", text="目前已具备材料有哪些？（多选）",
    dimension="product_supply_chain", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="产品检测报告", feasibility_score=2, lead_score=1),
        QuestionOption(id="B", text="出口国家合规认证", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="英文产品目录及报价", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="有成熟合作的货代/报关机构", feasibility_score=1, lead_score=1),
    ], max_feasibility_score=2, max_lead_score=1, cap_note="多选累加，封顶 F:2 / L:1",
)

Q15 = Question(
    id="Q15", text="你的交付能力是否稳定？",
    dimension="product_supply_chain", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="产能、交期、品质、售后都稳定", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="大部分稳定，偶尔需要协调", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="小单稳定，大单有压力", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="旺季或大单容易出问题", feasibility_score=0, lead_score=0),
        QuestionOption(id="E", text="交付周期、质量或售后存在明显不确定性", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=2,
)

Q16 = Question(
    id="Q16", text="公司是否有标准化的业务流程SOP（如报价、打样、跟单、发货等）？",
    dimension="product_supply_chain", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="有完备且严格执行的SOP", feasibility_score=2, lead_score=2),
        QuestionOption(id="B", text="有一些流程规范，但尚未完全标准化", feasibility_score=1, lead_score=1),
        QuestionOption(id="C", text="正在建立或打算建立", feasibility_score=1, lead_score=0),
        QuestionOption(id="D", text="没有标准流程，主要靠人协调", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=2,
)

# ── 维度四：出海路径清晰度（F:10 / L:8）──

Q17 = Question(
    id="Q17", text="你目前还考虑增加哪些出海方式？（多选）",
    dimension="path_clarity", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="海外建厂、建仓、建分公司", feasibility_score=2, lead_score=2),
        QuestionOption(id="B", text="海外展会", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="阿里国际站等B2B平台", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="海外货架电商：Amazon/TikTok Shop等", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="海外独立站", feasibility_score=2, lead_score=2),
        QuestionOption(id="F", text="海外短视频出海", feasibility_score=2, lead_score=2),
        QuestionOption(id="G", text="Google/Facebook广告投放", feasibility_score=1, lead_score=1),
        QuestionOption(id="H", text="还不知道怎么选", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=2, cap_note="多选累加，封顶 F:2 / L:2",
)

Q18 = Question(
    id="Q18", text="企业出海中，你最担心什么？",
    dimension="path_clarity", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="投入太大，怕打水漂", feasibility_score=1, lead_score=1),
        QuestionOption(id="B", text="不知道哪个国家适合", feasibility_score=1, lead_score=2),
        QuestionOption(id="C", text="担心没有团队执行", feasibility_score=1, lead_score=2),
        QuestionOption(id="D", text="担心产品合规和认证", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="担心海外客户不成交", feasibility_score=1, lead_score=2),
        QuestionOption(id="F", text="不知道第一步怎么做", feasibility_score=0, lead_score=3),
    ], max_feasibility_score=2, max_lead_score=3,
)

Q19 = Question(
    id="Q19", text="你能接受的每月出海试错成本是多少？",
    dimension="path_clarity", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="10万元以上", feasibility_score=3, lead_score=2),
        QuestionOption(id="B", text="5万-10万元", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="2万-5万元", feasibility_score=2, lead_score=1),
        QuestionOption(id="D", text="5000元-2万元", feasibility_score=1, lead_score=0),
        QuestionOption(id="E", text="暂时没有明确预算", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=2,
)

Q20 = Question(
    id="Q20", text="你更倾向的投入方式？",
    dimension="path_clarity", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="愿意长期布局，只要方向正确", feasibility_score=2, lead_score=1),
        QuestionOption(id="B", text="愿意投入，但希望看到阶段结果", feasibility_score=2, lead_score=1),
        QuestionOption(id="C", text="希望先低成本测试，再决定加大投入", feasibility_score=1, lead_score=0),
        QuestionOption(id="D", text="预算有限，只能小步快跑", feasibility_score=0, lead_score=0),
        QuestionOption(id="E", text="先了解，不一定投入", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=2, max_lead_score=1,
)

Q21 = Question(
    id="Q21", text="你愿意把出海预算花在哪里？",
    dimension="path_clarity", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="出海班子搭建", feasibility_score=1, lead_score=2),
        QuestionOption(id="B", text="海外社媒营销", feasibility_score=1, lead_score=2),
        QuestionOption(id="C", text="展会/独立站/B2B平台", feasibility_score=1, lead_score=2),
        QuestionOption(id="D", text="还没想清楚", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=1, max_lead_score=2,
)

# ── 维度五：短视频获客适配度（F:20 / L:15）──

Q22 = Question(
    id="Q22", text="你们企业现在有没有新媒体团队？",
    dimension="content_fitness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="有成熟新媒体团队，能拍、能剪、能运营", feasibility_score=5, lead_score=3),
        QuestionOption(id="B", text="有拍剪或运营人员，但不系统", feasibility_score=3, lead_score=2),
        QuestionOption(id="C", text="有国内新媒体经验，但没做过海外", feasibility_score=3, lead_score=2),
        QuestionOption(id="D", text="没有团队，但老板愿意亲自参与", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="完全没有新媒体基础，也没人负责", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=5, max_lead_score=3,
)

Q23 = Question(
    id="Q23", text="你现在是否做过海外社媒或短视频？",
    dimension="content_fitness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="已经做了，有内容体系，有询盘成交", feasibility_score=5, lead_score=3),
        QuestionOption(id="B", text="已经做了，没有形成体系，有少量询盘", feasibility_score=3, lead_score=2),
        QuestionOption(id="C", text="想做，不知道拍什么内容和选哪个平台", feasibility_score=1, lead_score=1),
    ], max_feasibility_score=5, max_lead_score=3,
)

Q24 = Question(
    id="Q24", text="目前做过哪些社媒平台？（多选）",
    dimension="content_fitness", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="国内：抖音/快手/视频号/小红书", feasibility_score=1, lead_score=1),
        QuestionOption(id="B", text="国外：TikTok/Facebook/Instagram/YouTube", feasibility_score=3, lead_score=2),
        QuestionOption(id="C", text="其他海外非主流平台", feasibility_score=1, lead_score=0),
        QuestionOption(id="D", text="都没做过", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=2, cap_note="多选累加，封顶 F:3 / L:2",
)

Q25 = Question(
    id="Q25", text="当前新媒体平台内容创造能力？",
    dimension="content_fitness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="能稳定推进，偶尔出爆款", feasibility_score=4, lead_score=3),
        QuestionOption(id="B", text="能发内容，但选题和转化弱", feasibility_score=2, lead_score=2),
        QuestionOption(id="C", text="偶尔拍，缺少持续性", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="外包做过，但效果一般", feasibility_score=1, lead_score=0),
        QuestionOption(id="E", text="完全没有内容能力", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=4, max_lead_score=3,
)

Q26 = Question(
    id="Q26", text="你们可以支持的拍摄场景？（多选）",
    dimension="content_fitness", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="工厂车间", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="B", text="生产流程", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="C", text="仓库库存", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="D", text="产品测试", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="E", text="质检过程", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="F", text="打包发货", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="G", text="客户反馈", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="H", text="客户案例", feasibility_score=0.3, lead_score=0.4),
        QuestionOption(id="I", text="展会素材", feasibility_score=0.3, lead_score=0.4),
    ], max_feasibility_score=3, max_lead_score=4,
    cap_note="每项 0.3F/0.4L，9 项全选 = F≈3/L≈4。已裁决保持 9 项，不补「海外订单」。",
    conflict_note="内容选项.md Q15 拍摄场景有 10 项（含「海外订单」），有出海经验题目.md 和 scoring-design 均为 9 项。已裁决：保持 9 项，不补。决议来源: docs/questionnaire-canonical.md",
)

# ── 维度六：销转承接能力（F:10 / L:15）──

Q27 = Question(
    id="Q27", text="海外客户来咨询，你们现在怎么承接？（多选）",
    dimension="conversion_readiness", kind="multiple_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="WhatsApp", feasibility_score=1, lead_score=2),
        QuestionOption(id="B", text="邮箱", feasibility_score=1, lead_score=1),
        QuestionOption(id="C", text="独立站表单/转化", feasibility_score=2, lead_score=2),
        QuestionOption(id="D", text="暂时没有承接路径", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=5, cap_note="多选累加，封顶 F:3 / L:5",
    conflict_note="内容选项.md 中 Q17 重复编号（承接渠道+销售资料 / 外贸团队+语言能力），有出海经验题目.md 和 scoring-design 已拆为 Q27/Q28/Q29",
)

Q28 = Question(
    id="Q28", text="目前的外贸团队情况？",
    dimension="conversion_readiness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="有成熟外贸团队，并能承接海外询盘", feasibility_score=3, lead_score=5),
        QuestionOption(id="B", text="有外贸人员，但获客和转化不稳定", feasibility_score=2, lead_score=3),
        QuestionOption(id="C", text="有销售团队，但主要做内销", feasibility_score=1, lead_score=1),
        QuestionOption(id="E", text="没有销售团队", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=5,
)

Q29 = Question(
    id="Q29", text="外贸团队语言能力？",
    dimension="conversion_readiness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="英语和小语种都能覆盖", feasibility_score=4, lead_score=5),
        QuestionOption(id="B", text="英语可以正常沟通", feasibility_score=3, lead_score=3),
        QuestionOption(id="C", text="英语一般，但能基础回复", feasibility_score=1, lead_score=1),
        QuestionOption(id="D", text="需要翻译工具辅助", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=4, max_lead_score=5,
)

# ── 维度七：企业出海行动力（F:5 / L:15）──

Q30 = Question(
    id="Q30", text="最想让出海顾问帮你解决什么问题？",
    dimension="action_readiness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="判断行业海外有没有机会", feasibility_score=2, lead_score=4),
        QuestionOption(id="B", text="判断哪个国家最适合先做", feasibility_score=2, lead_score=5),
        QuestionOption(id="C", text="选出最适合出海的主推产品", feasibility_score=2, lead_score=5),
        QuestionOption(id="D", text="给到海外客户画像建议", feasibility_score=1, lead_score=5),
        QuestionOption(id="E", text="不确定，希望顾问帮我整体诊断", feasibility_score=1, lead_score=7),
    ], max_feasibility_score=2, max_lead_score=7,
)

Q31 = Question(
    id="Q31", text="是否愿意预约50分钟1V1咨询？",
    dimension="action_readiness", kind="single_choice", branch="experienced",
    options=[
        QuestionOption(id="A", text="愿意，想尽快预约", feasibility_score=3, lead_score=8),
        QuestionOption(id="B", text="愿意，但想先看报告", feasibility_score=2, lead_score=6),
        QuestionOption(id="C", text="可以考虑，先简单了解", feasibility_score=1, lead_score=3),
        QuestionOption(id="D", text="暂时不考虑", feasibility_score=0, lead_score=0),
    ], max_feasibility_score=3, max_lead_score=8,
)

# ═══════════════════════════════════════════════════════════════
# 分支定义
# ═══════════════════════════════════════════════════════════════

ALL_QUESTIONS: list[Question] = [
    Q1, Q2a, Q2b, Q2c, Q3a, Q3b, Q3c, Q4,
    Q5,
    Q6, Q7, Q8, Q9, Q10a, Q10b, Q10c,
    Q11, Q12, Q13, Q14, Q15, Q16,
    Q17, Q18, Q19, Q20, Q21,
    Q22, Q23, Q24, Q25, Q26,
    Q27, Q28, Q29,
    Q30, Q31,
]

COMMON_QUESTIONS = [q for q in ALL_QUESTIONS if q.branch == "common"]
BRANCH_DECISION_QUESTION = Q5
EXPERIENCED_QUESTIONS = [q for q in ALL_QUESTIONS if q.branch == "experienced"]

EXPERIENCED_BRANCH = QuestionnaireBranch(
    id="experienced",
    name="有出海经验",
    description="Q5 选 A/B/C 的用户进入此分支，包含 Q1-Q4（公共）+ Q5（分流）+ Q6-Q31（有出海经验专属题目）。F/L 总分对齐 scoring-design.md：F≈100 / L≈100。",
    questions=COMMON_QUESTIONS + [Q5] + EXPERIENCED_QUESTIONS,
)

INEXPERIENCED_BRANCH = QuestionnaireBranch(
    id="inexperienced",
    name="无出海经验（占位）",
    description="Q5 选 D 的用户进入此分支。Q6-Q10 跳过（overseas_validation 维度计 0 分）。无出海经验题库尚未提供，当前分支仅包含公共题 Q1-Q4 和分流题 Q5。",
    questions=COMMON_QUESTIONS + [Q5],
)

SCORED_QUESTIONS = [q for q in ALL_QUESTIONS if q.is_scored]

# 逐题原始满分（raw_max）与产品维度权重（header_weight）对照。
# raw_max ≠ header_weight 是设计内的 —— 维度 header 是产品口径，
# answer_scoring.py 负责逐题 raw → 维度归一化到 header。
# Q1 信息完整度（F=2/L=3）已纳入 enterprise_base 计分。
UNALLOCATED_WEIGHT = {
    "feasibility": {"expected": 100, "actual_from_scored": 99, "delta": 1},
    "lead": {"expected": 100, "actual_from_scored": 102, "delta": -2},
}

DIMENSION_QUESTIONS: dict[str, list[Question]] = {}
for q in ALL_QUESTIONS:
    DIMENSION_QUESTIONS.setdefault(q.dimension, []).append(q)
