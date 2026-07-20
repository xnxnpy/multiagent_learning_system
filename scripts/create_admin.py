"""
创建管理员账号脚本
用法: python scripts/create_admin.py --username admin --password admin123
"""
import asyncio
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import AsyncSessionLocal, async_engine, Base
from app.models.user import User
from app.core.security import get_password_hash


async def create_admin(username: str, password: str, email: str = None, real_name: str = None):
    async with AsyncSessionLocal() as db:
        # 确保表存在
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from sqlalchemy import select

        result = await db.execute(select(User).where(User.username == username))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role == "admin":
                print(f"管理员 '{username}' 已存在，跳过")
                return
            # 升级为管理员
            existing.role = "admin"
            existing.password_hash = get_password_hash(password)
            if email:
                existing.email = email
            if real_name:
                existing.real_name = real_name
            await db.commit()
            print(f"用户 '{username}' 已升级为管理员")
            return

        # 创建新管理员
        admin = User(
            username=username,
            password_hash=get_password_hash(password),
            role="admin",
            real_name=real_name or username,
            email=email or f"{username}@admin.local",
        )
        db.add(admin)
        await db.commit()
        print(f"管理员 '{username}' 创建成功")


def main():
    parser = argparse.ArgumentParser(description="创建管理员账号")
    parser.add_argument("--username", required=True, help="用户名")
    parser.add_argument("--password", required=True, help="密码（至少6位）")
    parser.add_argument("--email", default=None, help="邮箱（可选）")
    parser.add_argument("--real_name", default=None, help="真实姓名（可选）")
    args = parser.parse_args()

    if len(args.password) < 6:
        print("错误：密码长度至少 6 位")
        sys.exit(1)

    asyncio.run(create_admin(args.username, args.password, args.email, args.real_name))


if __name__ == "__main__":
    main()
