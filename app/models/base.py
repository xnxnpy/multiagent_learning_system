from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
from app.core.logger import log

# 创建异步引擎
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_timeout=30,
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 创建基类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    from sqlalchemy import create_engine, text

    db_url = settings.SYNC_DATABASE_URL
    if 'mysql+pymysql://' in db_url:
        parts = db_url.split('/')
        base_url = '/'.join(parts[:-1]) + '/mysql'

        try:
            temp_engine = create_engine(base_url)
            with temp_engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{settings.MYSQL_DATABASE}'")
                )
                if not result.fetchone():
                    log.info(f"数据库 {settings.MYSQL_DATABASE} 不存在，正在创建...")
                    conn.execute(text(f"CREATE DATABASE {settings.MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    conn.commit()
                    log.info(f"数据库 {settings.MYSQL_DATABASE} 创建成功")
                else:
                    log.info(f"数据库 {settings.MYSQL_DATABASE} 已存在")
            temp_engine.dispose()
        except Exception as e:
            log.warning(f"自动创建数据库失败，请手动创建: {e}")


async def init_db():
    """初始化数据库（先创建数据库，再创建表，最后同步缺失列）"""
    # 先尝试创建数据库（如果不存在）
    await create_database_if_not_exists()

    # 然后创建表 + 同步缺失列
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        log.info("数据库表初始化成功")

        # 同步缺失的列（与 create_all 同一事务）
        def _sync_columns(sync_conn):
            from sqlalchemy import text, inspect as sa_inspect

            inspector = sa_inspect(sync_conn)
            dialect = sync_conn.dialect

            for table_name, table in Base.metadata.tables.items():
                existing_cols = {c['name'] for c in inspector.get_columns(table_name)}

                for col in table.columns:
                    if col.name in existing_cols:
                        continue

                    # 用 SQLAlchemy 编译列类型
                    col_type = col.type.compile(dialect=dialect)
                    parts = [f"`{col.name}`", col_type]

                    # 处理 server_default（func.now() 等）
                    if col.server_default is not None:
                        arg = col.server_default.arg
                        if hasattr(arg, 'text'):
                            # TextClause → 直接取 .text
                            parts.append(f"DEFAULT {arg.text}")
                        elif hasattr(arg, 'compile'):
                            # Function 对象（如 func.now()）→ 编译为 SQL
                            parts.append(f"DEFAULT {arg.compile(dialect=dialect)}")
                        else:
                            parts.append(f"DEFAULT {arg}")

                    # 处理 Python 层 default（非 server_default）
                    elif col.default is not None:
                        arg = col.default.arg
                        # 只处理 SQL 表达式类型的 default，纯 Python callable 跳过
                        from sqlalchemy.sql.elements import ColumnElement
                        if isinstance(arg, ColumnElement):
                            parts.append(f"DEFAULT {arg.compile(dialect=dialect)}")
                        elif isinstance(arg, str):
                            parts.append(f"DEFAULT '{arg}'")
                        elif isinstance(arg, (int, float)):
                            parts.append(f"DEFAULT {arg}")

                    if not col.nullable:
                        parts.append("NOT NULL")

                    if col.comment:
                        parts.append(f"COMMENT '{col.comment}'")

                    ddl = f"ALTER TABLE `{table_name}` ADD COLUMN {' '.join(parts)}"
                    sync_conn.execute(text(ddl))
                    log.info(f"自动添加列: {table_name}.{col.name}")

        await conn.run_sync(_sync_columns)

        # 同步缺失的索引（与 create_all 同一事务）
        def _sync_indexes(sync_conn):
            from sqlalchemy import text, inspect as sa_inspect

            inspector = sa_inspect(sync_conn)

            for table_name, table in Base.metadata.tables.items():
                existing_indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
                existing_unique = {idx['name'] for idx in inspector.get_unique_constraints(table_name)}

                for idx in table.indexes:
                    if idx.name in existing_indexes:
                        continue
                    col_names = [c.name for c in idx.columns]
                    cols_str = ", ".join(f"`{c}`" for c in col_names)
                    unique_str = "UNIQUE " if idx.unique else ""
                    ddl = f"CREATE {unique_str}INDEX `{idx.name}` ON `{table_name}` ({cols_str})"
                    try:
                        sync_conn.execute(text(ddl))
                        log.info(f"自动创建索引: {table_name}.{idx.name}")
                    except Exception as e:
                        log.warning(f"创建索引 {table_name}.{idx.name} 失败（可能已存在）: {e}")

        await conn.run_sync(_sync_indexes)

        # ── 多画像迁移：删除旧 UNIQUE 索引、创建普通索引 ──
        def _migrate_multi_profile(sync_conn):
            from sqlalchemy import text, inspect as sa_inspect

            inspector = sa_inspect(sync_conn)

            # 1) student_profiles: 删除 user_id 上的旧 UNIQUE 索引
            for idx in inspector.get_indexes("student_profiles"):
                if idx.get("unique") and idx["column_names"] == ["user_id"]:
                    ddl = f"DROP INDEX `{idx['name']}` ON `student_profiles`"
                    try:
                        sync_conn.execute(text(ddl))
                        log.info(f"已删除旧唯一索引: student_profiles.{idx['name']}")
                    except Exception as e:
                        log.warning(f"删除索引 {idx['name']} 失败: {e}")

            # 2) 删除可能存在的旧联合唯一索引（改为普通索引）
            for idx in inspector.get_indexes("student_profiles"):
                if idx.get("unique") and set(idx["column_names"]) == {"user_id", "is_active"}:
                    ddl = f"DROP INDEX `{idx['name']}` ON `student_profiles`"
                    try:
                        sync_conn.execute(text(ddl))
                        log.info(f"已删除旧联合唯一索引: student_profiles.{idx['name']}")
                    except Exception as e:
                        log.warning(f"删除索引 {idx['name']} 失败: {e}")

            # 3) 创建普通（非唯一）索引
            existing_indexes = {idx["name"] for idx in inspector.get_indexes("student_profiles")}
            if "idx_student_profiles_user_active" not in existing_indexes:
                try:
                    sync_conn.execute(text(
                        "CREATE INDEX `idx_student_profiles_user_active` "
                        "ON `student_profiles` (`user_id`, `is_active`)"
                    ))
                    log.info("已创建普通索引: student_profiles.(user_id, is_active)")
                except Exception as e:
                    log.warning(f"创建索引失败（可能已存在）: {e}")

            # 3) learning_paths: 旧唯一索引 uk_lp_user_id → 包含 profile_id
            for idx in inspector.get_indexes("learning_paths"):
                if idx.get("unique") and idx["column_names"] == ["user_id"] and idx["name"] == "uk_lp_user_id":
                    sync_conn.execute(text(f"DROP INDEX `uk_lp_user_id` ON `learning_paths`"))
                    log.info("已删除 learning_paths.uk_lp_user_id")
            lp_indexes = {idx["name"] for idx in inspector.get_indexes("learning_paths")}
            if "uk_lp_user_profile" not in lp_indexes:
                try:
                    sync_conn.execute(text(
                        "CREATE UNIQUE INDEX `uk_lp_user_profile` "
                        "ON `learning_paths` (`user_id`, `profile_id`)"
                    ))
                    log.info("已创建 learning_paths 唯一索引: (user_id, profile_id)")
                except Exception as e:
                    log.warning(f"创建 learning_paths 索引失败: {e}")

            # 4) learning_resources: 旧唯一索引 → 包含 profile_id
            for idx in inspector.get_indexes("learning_resources"):
                if idx.get("unique") and idx["name"] == "uk_lr_user_stage_type_topic":
                    sync_conn.execute(text(f"DROP INDEX `uk_lr_user_stage_type_topic` ON `learning_resources`"))
                    log.info("已删除 learning_resources.uk_lr_user_stage_type_topic")
            lr_indexes = {idx["name"] for idx in inspector.get_indexes("learning_resources")}
            if "uk_lr_res_profile_stage_type_topic" not in lr_indexes:
                try:
                    sync_conn.execute(text(
                        "CREATE UNIQUE INDEX `uk_lr_res_profile_stage_type_topic` "
                        "ON `learning_resources` (`user_id`, `profile_id`, `stage_id`, `resource_type`, `topic`)"
                    ))
                    log.info("已创建 learning_resources 唯一索引: (user_id, profile_id, stage_id, resource_type, topic)")
                except Exception as e:
                    log.warning(f"创建 learning_resources 索引失败: {e}")

        await conn.run_sync(_migrate_multi_profile)

        # ── 多画像数据初始化：给现有用户创建默认画像，回填 profile_id ──
        def _init_multi_profile_data(sync_conn):
            from sqlalchemy import text

            # 0) 清理重复画像：每个用户只保留最早的一条 is_active=1 的画像，
            #    其余设为 is_active=0（避免外键约束问题，不直接删除）
            sync_conn.execute(text("""
                UPDATE student_profiles sp1
                SET sp1.is_active = FALSE
                WHERE sp1.is_active = TRUE
                AND sp1.id NOT IN (
                    SELECT sub.min_id FROM (
                        SELECT MIN(sp2.id) AS min_id
                        FROM student_profiles sp2
                        WHERE sp2.is_active = TRUE
                        GROUP BY sp2.user_id
                    ) sub
                )
            """))

            # 1) 给没有画像的用户创建默认画像
            sync_conn.execute(text("""
                INSERT INTO student_profiles (user_id, profile_name, is_active, is_archived)
                SELECT u.id, '默认画像', TRUE, FALSE
                FROM users u
                WHERE u.role = 'student'
                AND NOT EXISTS (
                    SELECT 1 FROM student_profiles sp WHERE sp.user_id = u.id
                )
            """))

            # 2) 确保所有已有画像 is_active 不为 NULL
            sync_conn.execute(text("""
                UPDATE student_profiles SET is_active = TRUE WHERE is_active IS NULL
            """))

            # 3) 回填 learning_paths.profile_id
            sync_conn.execute(text("""
                UPDATE learning_paths lp
                JOIN student_profiles sp ON sp.user_id = lp.user_id AND sp.is_active = TRUE
                SET lp.profile_id = sp.id
                WHERE lp.profile_id IS NULL
            """))

            # 4) 回填 profile_chat_messages.profile_id
            sync_conn.execute(text("""
                UPDATE profile_chat_messages pcm
                JOIN student_profiles sp ON sp.user_id = pcm.user_id AND sp.is_active = TRUE
                SET pcm.profile_id = sp.id
                WHERE pcm.profile_id IS NULL
            """))

            # 5) 回填 learning_resources.profile_id
            sync_conn.execute(text("""
                UPDATE learning_resources lr
                JOIN student_profiles sp ON sp.user_id = lr.user_id AND sp.is_active = TRUE
                SET lr.profile_id = sp.id
                WHERE lr.profile_id IS NULL
            """))

            log.info("多画像数据初始化完成")

        try:
            await conn.run_sync(_init_multi_profile_data)
        except Exception as e:
            log.warning(f"多画像数据初始化跳过（可能已执行）: {e}")