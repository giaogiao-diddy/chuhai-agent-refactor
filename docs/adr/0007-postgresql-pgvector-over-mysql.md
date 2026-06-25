# 0007-postgresql-pgvector-over-mysql

## 决策：PostgreSQL 16+ + pgvector 替代 MySQL 8.x

**状态**：accepted | **替代**：[ADR-0003](0003-mysql-over-cloudbase-nosql.md)

**背景**：ADR-0003 决定使用 MySQL 8.x。但 ADR-0006（向量 RAG）依赖 pgvector，而 pgvector 是 PostgreSQL 扩展，无法在 MySQL 上运行。如不调整，将迫使引入独立向量数据库（Qdrant/Milvus），增加双系统维护成本。

**决策**：将关系型数据库从 MySQL 8.x 切换为 PostgreSQL 16+，并启用 pgvector 扩展。

**原因**：
1. PRD 和 ADR-0006 已明确需要向量 RAG，pgvector 是 PostgreSQL 原生扩展
2. 一套 PostgreSQL 同时满足 ACID 事务（reports + lead_reports 原子写入）和向量检索（知识库语义召回）
3. SQLAlchemy 2.0 对 PostgreSQL 支持成熟，asyncpg 性能优于 asyncmy
4. 避免 MySQL + 独立向量库的双系统运维开销
5. 业务数据（用户/题目/答案/报告）与 RAG 知识块可统一建模、统一迁移、统一备份

**技术细节**：
- PostgreSQL 16+（pgvector 0.7+ 推荐 PG16+）
- pgvector 扩展：`CREATE EXTENSION vector;`
- SQLAlchemy 2.0 async 引擎：`asyncpg` 驱动
- 向量字段：`knowledge_base.embedding vector(1536)`（取决于 embedding 模型维度）
- 检索：余弦相似度 `<=>` 操作符 + IVFFlat/HNSW 索引

**后果**：
- 需要安装 PostgreSQL 16+（CloudBase 支持 PostgreSQL，或用独立实例）
- 数据库连接串从 `mysql+asyncmy://` 改为 `postgresql+asyncpg://`
- Alembic 迁移需要从零开始（不能复用 MySQL 迁移）
- 旧 CloudBase NoSQL 数据无迁移路径（已决策全弃）
