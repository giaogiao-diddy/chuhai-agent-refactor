from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_document import RagDocument
from app.schemas.rag import RagDocumentMatch
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
