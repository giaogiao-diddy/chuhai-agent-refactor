import uuid as _uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_document import RagDocument
from app.schemas.rag import KnowledgeSearchResult, RagDocumentMatch
from app.services.deepseek_client import DeepSeekClient

SEED_DOCUMENTS = [
    {
        "title": "东南亚市场B2B工厂出海要点",
        "content": "东南亚（越南、泰国、印尼、马来西亚）是中国工厂出海首选区域。关税优势明显，物流成本低。B2B买家偏好源头工厂直接合作，重视交期稳定性和认证资质。建议优先从阿里国际站和当地展会切入。",
        "source": "出海行业知识库",
    },
    {
        "title": "TikTok短视频B2B获客策略",
        "content": "TikTok已成为B2B工厂获客新渠道。工厂车间、生产流程、质检过程、打包发货等场景拍摄内容能展示真实制造能力。建议每周发布3-5条短视频，搭配WhatsApp承接询盘。B2B买家通过视频判断工厂规模和产品质量。",
        "source": "出海行业知识库",
    },
    {
        "title": "海外询盘承接最佳实践",
        "content": "WhatsApp是海外B2B买家最常用的沟通工具，需确保团队有人能英语回复。询盘承接黄金窗口期为24小时内。建议准备英文产品目录、报价模板和公司介绍PDF。海外买家重视响应速度和专业度。",
        "source": "出海行业知识库",
    },
    {
        "title": "产品出口认证与合规基础",
        "content": "出口不同国家需要不同认证：欧盟需要CE认证，美国需要FDA/FCC（视产品），东南亚多数国家接受CE或本国SNI等标准。建议先确认目标市场强制认证要求，避免货到港口无法清关。认证周期通常2-6个月。",
        "source": "出海行业知识库",
    },
    {
        "title": "独立站和Google广告出海获客",
        "content": "独立站是品牌出海的长线投入，搭配Google广告可以精准获客。建议先做英文独立站（Shopify/WooCommerce），产品详情页要专业（多角度图片、参数表格、工厂实力展示）。广告投放从搜索广告起步，逐步扩展到购物广告和再营销。",
        "source": "出海行业知识库",
    },
    {
        "title": "海外展会参展与客户跟进",
        "content": "海外展会（CES、IFA、广交会海外场、东南亚专业展）是B2B工厂获客的重要渠道。展前需准备英文产品目录、名片、样品。展后48小时内发送跟进邮件，附上产品资料和报价。展会获客成本约2000-5000元/条有效线索。",
        "source": "出海行业知识库",
    },
    {
        "title": "B2B工厂出海团队搭建建议",
        "content": "最小出海团队配置：1名外贸业务员（英语）、1名运营（拍剪+社媒）、1名跟单。预算有限时可老板亲自参与社媒内容出镜，建立工厂IP。外贸业务员建议底薪+提成，提成比例通常为毛利的10-20%。",
        "source": "出海行业知识库",
    },
    {
        "title": "出海目标市场选择方法论",
        "content": "选择出海目标市场需考虑：关税和贸易壁垒、本地竞争格局、物流便利性、文化语言障碍、汇率风险。欧美市场利润高但门槛高，东南亚市场门槛低但价格敏感，中东市场大单多但付款周期长。建议优先选择已有客户或询盘的市场试水。",
        "source": "出海行业知识库",
    },
    {
        "title": "东南亚跨境物流与清关指南",
        "content": "东南亚跨境物流主要渠道：海运（15-30天）、空运（3-7天）、陆运（中越/中老铁路，3-5天）。清关需提供商业发票、装箱单、原产地证、提单。各国关税查询可在WTO关税数据库或各国海关官网查询。建议与当地清关代理合作，避免因单证不全导致货物滞留港口产生滞港费。",
        "source": "出海行业知识库",
    },
    {
        "title": "海外品牌定位与本地化策略",
        "content": "品牌出海不是简单的翻译+上架。需要根据目标市场的消费习惯、文化背景和竞争格局做本地化。包括：品牌名本地化（避免文化歧义）、产品包装文字调整、定价策略（考虑当地购买力）、营销文案语气调整。建议先在目标市场找本地合作伙伴做市场调研，避免闭门造车。",
        "source": "出海行业知识库",
    },
    {
        "title": "B2B工厂海外社交媒体运营指南",
        "content": "海外社媒运营的核心平台：LinkedIn（B2B首选）、Facebook（东南亚B2B活跃）、Instagram（视觉产品展示）、YouTube（工厂纪录片/工艺流程）。内容策略：每周3-5条发布，其中60%展示制造能力和品质，30%展示客户案例，10%公司文化。使用Hashtag精准触达海外采购决策者。运营3-6个月可见询盘增长。",
        "source": "出海行业知识库",
    },
    {
        "title": "海外定价策略与利润模型",
        "content": "B2B出口定价公式：出厂价 + 海运费 + 关税 + 目的港杂费 + 经销商利润 + 风险缓冲 = 海外批发价。建议海外批发价为出厂价的2-3倍。定价需考虑：竞品当地售价、汇率波动缓冲（预留5-10%）、最小起订量对应的阶梯定价。不要用国内成本思维定价，海外客户对高性价比的接受度更高。",
        "source": "出海行业知识库",
    },
]


async def upsert_seed_documents(db: AsyncSession) -> int:
    client = DeepSeekClient()
    count = 0

    for doc in SEED_DOCUMENTS:
        existing = await db.scalar(
            select(RagDocument).where(RagDocument.title == doc["title"])
        )
        if existing is not None:
            continue

        embedding = await client.embed_text(doc["content"])
        rag_doc = RagDocument(
            title=doc["title"],
            content=doc["content"],
            source=doc.get("source"),
            embedding=embedding,
        )
        db.add(rag_doc)
        count += 1

    await db.flush()
    return count


async def search_rag_context(
    db: AsyncSession, query: str, top_k: int = 3
) -> list[RagDocumentMatch]:
    client = DeepSeekClient()
    query_embedding = await client.embed_text(query)

    stmt = (
        select(
            RagDocument.title,
            RagDocument.content,
            RagDocument.source,
            RagDocument.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(RagDocument.embedding.isnot(None))
        .order_by(text("distance"))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    rows = result.all()

    matches: list[RagDocumentMatch] = []
    for row in rows:
        score = max(0.0, 1.0 - float(row.distance))
        matches.append(RagDocumentMatch(
            title=row.title,
            content=row.content,
            source=row.source,
            score=round(score, 4),
        ))
    return matches


# ── CRUD ──

async def list_knowledge(db: AsyncSession):
    """返回轻量 rows，不加载 embedding 向量。"""
    stmt = select(
        RagDocument.id,
        RagDocument.title,
        RagDocument.source,
        RagDocument.content,
        RagDocument.created_at,
        (RagDocument.embedding.isnot(None)).label("has_embedding"),
    ).order_by(RagDocument.created_at.desc())
    result = await db.execute(stmt)
    return result.all()


async def get_knowledge(db: AsyncSession, doc_id: _uuid.UUID) -> RagDocument | None:
    return await db.get(RagDocument, doc_id)


async def create_knowledge(db: AsyncSession, title: str, content: str, source: str | None) -> RagDocument:
    client = DeepSeekClient()
    embedding = await client.embed_text(content)
    doc = RagDocument(title=title, content=content, source=source, embedding=embedding)
    db.add(doc)
    await db.flush()
    return doc


async def update_knowledge(
    db: AsyncSession, doc_id: _uuid.UUID,
    title: str | None, content: str | None, source: str | None,
    update_source: bool = False,
) -> RagDocument | None:
    doc = await db.get(RagDocument, doc_id)
    if doc is None:
        return None
    if title is not None:
        doc.title = title
    if update_source:
        doc.source = source  # None = 清空
    content_changed = False
    if content is not None and content != doc.content:
        doc.content = content
        content_changed = True
    if content_changed:
        client = DeepSeekClient()
        doc.embedding = await client.embed_text(doc.content)
    await db.flush()
    return doc


async def delete_knowledge(db: AsyncSession, doc_id: _uuid.UUID) -> bool:
    doc = await db.get(RagDocument, doc_id)
    if doc is None:
        return False
    await db.delete(doc)
    await db.flush()
    return True


async def re_embed_knowledge(db: AsyncSession, doc_id: _uuid.UUID) -> RagDocument | None:
    doc = await db.get(RagDocument, doc_id)
    if doc is None:
        return None
    client = DeepSeekClient()
    doc.embedding = await client.embed_text(doc.content)
    await db.flush()
    return doc


async def search_knowledge(db: AsyncSession, query: str, top_k: int = 5) -> list[KnowledgeSearchResult]:
    client = DeepSeekClient()
    query_embedding = await client.embed_text(query)
    stmt = (
        select(
            RagDocument.title,
            RagDocument.content,
            RagDocument.source,
            RagDocument.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(RagDocument.embedding.isnot(None))
        .order_by(text("distance"))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    rows = result.all()
    results: list[KnowledgeSearchResult] = []
    for row in rows:
        preview = row.content[:200] + "..." if len(row.content) > 200 else row.content
        results.append(KnowledgeSearchResult(
            title=row.title,
            source=row.source,
            content_preview=preview,
            distance=round(float(row.distance), 4),
        ))
    return results
