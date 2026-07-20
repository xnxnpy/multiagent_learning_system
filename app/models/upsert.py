"""
MySQL upsert 工具函数
基于 INSERT ... ON DUPLICATE KEY UPDATE，利用唯一索引实现幂等写入
"""
from typing import Dict, Any, Type
from sqlalchemy import Table, Column
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert(
    db: AsyncSession,
    table: Table,
    values: Dict[str, Any],
    update_cols: list[str] | None = None,
) -> None:
    """
    MySQL upsert：插入或更新（基于唯一索引冲突）

    Args:
        db: 异步数据库会话
        table: SQLAlchemy Table 对象（如 LearningResource.__table__）
        values: 要写入的字段值 dict
        update_cols: 冲突时要更新的字段列表，默认更新 values 中除主键外的所有字段
    """
    stmt = mysql_insert(table).values(**values)

    if update_cols is None:
        # 默认更新 values 中除主键以外的所有字段
        pk_cols = {c.name for c in table.primary_key.columns}
        update_cols = [k for k in values if k not in pk_cols]

    # 构建 ON DUPLICATE KEY UPDATE
    update_dict = {col: stmt.inserted[col] for col in update_cols}
    # 同时更新 updated_at（如果表有这个字段）
    if "updated_at" in table.columns:
        from sqlalchemy import func
        update_dict["updated_at"] = func.now()

    stmt = stmt.on_duplicate_key_update(**update_dict)
    await db.execute(stmt)
