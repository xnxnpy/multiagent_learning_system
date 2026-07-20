# -*- coding: utf-8 -*-
"""阿里云 OSS 上传测试

运行方式:
  conda activate multi_agent
  python test_oss_upload.py

前置条件:
  - .env 中配置 OSS_ACCESS_KEY_ID、OSS_ACCESS_KEY_SECRET、OSS_BUCKET_NAME、OSS_ENDPOINT
  - pip install oss2
"""
import asyncio
import os
import tempfile

os.environ.setdefault("APP_NAME", "test")

from app.core.config import settings


def print_config():
    """打印当前 OSS 配置（隐藏密钥）"""
    print("=" * 60)
    print("当前 OSS 配置")
    print("=" * 60)
    print(f"  ACCESS_KEY_ID:  {settings.OSS_ACCESS_KEY_ID[:8]}..." if settings.OSS_ACCESS_KEY_ID else "  ACCESS_KEY_ID:  (空)")
    print(f"  BUCKET_NAME:    {settings.OSS_BUCKET_NAME}" if settings.OSS_BUCKET_NAME else "  BUCKET_NAME:    (空)")
    print(f"  ENDPOINT:       {settings.OSS_ENDPOINT}")
    print(f"  BASE_URL:       {settings.OSS_BASE_URL or '(空，使用默认格式)'}")
    print()


async def test_upload():
    """测试 OSS 上传"""
    from app.multimodal.oss_uploader import OSSUploader

    # 检查配置
    if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_BUCKET_NAME:
        print("[SKIP] OSS 未配置，请在 .env 中填写：")
        print("  OSS_ACCESS_KEY_ID=你的AccessKey ID")
        print("  OSS_ACCESS_KEY_SECRET=你的AccessKey Secret")
        print("  OSS_BUCKET_NAME=你的Bucket名称")
        print("  OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com")
        print()
        print("获取方式：")
        print("  1. 登录阿里云控制台 → RAM 访问控制 → AccessKey 管理")
        print("  2. OSS 控制台 → Bucket 列表 → 你的 Bucket → 基础设置 → 区域")
        return

    # 创建一个临时测试文件
    test_dir = tempfile.mkdtemp(prefix="oss_test_")
    test_file = os.path.join(test_dir, "test_video.mp4")

    # 生成一个小的测试文件（100KB 随机数据）
    with open(test_file, "wb") as f:
        f.write(os.urandom(100 * 1024))
    print(f"测试文件: {test_file} ({os.path.getsize(test_file)} bytes)")

    # 测试 key 和 URL 构建
    uploader = OSSUploader()
    key = uploader._build_key(user_id=999, stage_id=0)
    url = uploader._build_url(key)
    print(f"OSS Key: {key}")
    print(f"访问 URL: {url}")
    print()

    # 上传
    print("开始上传 ...")
    result = await uploader.upload_video(test_file, user_id=999, stage_id=0)

    if result["success"]:
        print(f"[OK] 上传成功!")
        print(f"  URL:     {result['url']}")
        print(f"  OSS Key: {result['oss_key']}")
        print()
        print("请在浏览器中打开上面的 URL 验证文件是否可访问。")
        print("如果返回 403，检查 Bucket 的读写权限设置。")
    else:
        print(f"[FAIL] 上传失败: {result['error']}")

    # 清理
    os.remove(test_file)
    os.rmdir(test_dir)
    print()
    print("临时文件已清理。")


if __name__ == "__main__":
    print_config()
    asyncio.run(test_upload())
