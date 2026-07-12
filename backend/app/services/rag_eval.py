"""RAG 离线评估集 — 30 条 query × 12 篇文档的 recall/precision/MRR 评估

评估指标:
- Recall@K: 系统召回的与query相关的文档数 / 所有应召回的文档数
- Precision@K: 系统召回的与query相关的文档数 / K
- MRR: 第一个相关文档的排名倒数 的平均值
- Hit@K: TopK 中至少命中一个相关文档的比例
"""

EVAL_QUERIES: list[dict] = [
    # ── 东南亚市场B2B工厂出海要点 ──
    {"query": "东南亚市场B2B工厂怎么出海", "relevant_titles": ["东南亚市场B2B工厂出海要点"]},
    {"query": "中国工厂出口东南亚有什么优势", "relevant_titles": ["东南亚市场B2B工厂出海要点"]},
    {"query": "越南泰国印尼哪个适合建厂", "relevant_titles": ["东南亚市场B2B工厂出海要点", "出海目标市场选择方法论"]},

    # ── TikTok短视频B2B获客策略 ──
    {"query": "TikTok怎么做B2B获客", "relevant_titles": ["TikTok短视频B2B获客策略"]},
    {"query": "工厂拍短视频能接到海外订单吗", "relevant_titles": ["TikTok短视频B2B获客策略"]},
    {"query": "短视频展示工厂车间生产流程", "relevant_titles": ["TikTok短视频B2B获客策略", "B2B工厂海外社交媒体运营指南"]},

    # ── 海外询盘承接最佳实践 ──
    {"query": "WhatsApp接海外询盘怎么回复", "relevant_titles": ["海外询盘承接最佳实践"]},
    {"query": "询盘来了24小时没回复会怎样", "relevant_titles": ["海外询盘承接最佳实践"]},
    {"query": "英文产品目录和报价模板怎么准备", "relevant_titles": ["海外询盘承接最佳实践"]},

    # ── 产品出口认证与合规基础 ──
    {"query": "出口欧盟需要什么认证", "relevant_titles": ["产品出口认证与合规基础"]},
    {"query": "CE认证多久能拿到", "relevant_titles": ["产品出口认证与合规基础"]},
    {"query": "美国FDA和东南亚SNI认证区别", "relevant_titles": ["产品出口认证与合规基础"]},

    # ── 独立站和Google广告出海获客 ──
    {"query": "独立站出海怎么做", "relevant_titles": ["独立站和Google广告出海获客"]},
    {"query": "Shopify和WooCommerce哪个好", "relevant_titles": ["独立站和Google广告出海获客"]},
    {"query": "Google广告投放从搜索到购物广告", "relevant_titles": ["独立站和Google广告出海获客"]},

    # ── 海外展会参展与客户跟进 ──
    {"query": "参加海外展会怎么准备", "relevant_titles": ["海外展会参展与客户跟进"]},
    {"query": "CES展会对B2B工厂有用吗", "relevant_titles": ["海外展会参展与客户跟进"]},
    {"query": "展会后48小时怎么跟进客户", "relevant_titles": ["海外展会参展与客户跟进"]},

    # ── B2B工厂出海团队搭建建议 ──
    {"query": "出海团队最少要几个人", "relevant_titles": ["B2B工厂出海团队搭建建议"]},
    {"query": "外贸业务员底薪提成怎么定", "relevant_titles": ["B2B工厂出海团队搭建建议"]},
    {"query": "老板自己拍短视频建立IP可以吗", "relevant_titles": ["B2B工厂出海团队搭建建议", "B2B工厂海外社交媒体运营指南"]},

    # ── 出海目标市场选择方法论 ──
    {"query": "怎么选择出海目标市场", "relevant_titles": ["出海目标市场选择方法论"]},
    {"query": "欧美和东南亚市场怎么选", "relevant_titles": ["出海目标市场选择方法论", "东南亚市场B2B工厂出海要点"]},
    {"query": "中东市场适合B2B工厂吗", "relevant_titles": ["出海目标市场选择方法论"]},

    # ── 东南亚跨境物流与清关指南 ──
    {"query": "东南亚跨境物流怎么走", "relevant_titles": ["东南亚跨境物流与清关指南"]},
    {"query": "清关需要准备什么单证", "relevant_titles": ["东南亚跨境物流与清关指南"]},
    {"query": "海运到泰国要多久", "relevant_titles": ["东南亚跨境物流与清关指南"]},

    # ── 海外品牌定位与本地化策略 ──
    {"query": "品牌出海怎么做本地化", "relevant_titles": ["海外品牌定位与本地化策略"]},
    {"query": "产品包装到海外要改吗", "relevant_titles": ["海外品牌定位与本地化策略"]},

    # ── B2B工厂海外社交媒体运营指南 ──
    {"query": "LinkedIn和Facebook做B2B怎么选", "relevant_titles": ["B2B工厂海外社交媒体运营指南"]},
    {"query": "海外社媒发什么内容能接到询盘", "relevant_titles": ["B2B工厂海外社交媒体运营指南"]},

    # ── 海外定价策略与利润模型 ──
    {"query": "出口到海外怎么定价", "relevant_titles": ["海外定价策略与利润模型"]},
    {"query": "海外批发价是出厂价的几倍", "relevant_titles": ["海外定价策略与利润模型"]},
]
