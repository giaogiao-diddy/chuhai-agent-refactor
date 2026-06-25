# 0003-mysql-over-cloudbase-nosql

> **状态**：superseded by [ADR-0007](0007-postgresql-pgvector-over-mysql.md)（已切换为 PostgreSQL + pgvector）

## 决策（已废弃）：迁移到 MySQL 关系型数据库

**背景**：旧 CloudBase 链路使用 NoSQL 文档数据库，数据通过不同集合物理隔离（reports / lead_reports）。切换到 Python FastAPI 独立部署后，关系型数据库在数据完整性、事务、查询灵活性上更适合。

**决策**：使用 MySQL 8.x + SQLAlchemy 2.0 + Alembic 迁移，替换 CloudBase NoSQL。

**原因**：
- 题库数据（questions / options）天然是关系型结构，NoSQL 查询需要额外代码对齐
- AI 报告的用户版/顾问版隔离在关系型中可以通过列级权限或视图实现，更优雅
- Python 生态中 SQLAlchemy 是最成熟的 ORM，与 FastAPI 集成无缝
- 原 CLAUDE.md 最初就计划用 MySQL，此决策回归原始技术方案

**后果**：
- CloudBase NoSQL 中现有 11 个集合的数据结构需要转为 SQLAlchemy 模型
- 需要管理数据库连接池（FastAPI 异步模式下用 asyncmy/sqlalchemy[asyncio]）
- CloudBase MySQL 或自建 MySQL 均可作为部署目标
- 弃用 CloudBase 数据库 SDK，改用标准 SQLAlchemy Session
