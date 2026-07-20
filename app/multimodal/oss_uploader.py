"""阿里云 OSS 视频上传器"""
import os
from app.core.config import settings
from app.core.logger import log
from app.core.ppt_video_config import OSS_VIDEO_KEY_TEMPLATE


class OSSUploader:
    """阿里云 OSS 上传封装"""

    def __init__(
        self,
        access_key_id: str = None,
        access_key_secret: str = None,
        bucket_name: str = None,
        endpoint: str = None,
        base_url: str = None,
    ):
        self.access_key_id = access_key_id or settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or settings.OSS_ACCESS_KEY_SECRET
        self.bucket_name = bucket_name or settings.OSS_BUCKET_NAME
        self.endpoint = endpoint or settings.OSS_ENDPOINT
        self.base_url = base_url or settings.OSS_BASE_URL

    def _build_key(self, user_id: int, stage_id: int) -> str:
        return OSS_VIDEO_KEY_TEMPLATE.format(user_id=user_id, stage_id=stage_id)

    def _build_url(self, key: str) -> str:
        if self.base_url:
            return f"{self.base_url}/{key}"
        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    def _get_bucket(self):
        """延迟初始化 OSS Bucket"""
        import oss2
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        return oss2.Bucket(auth, self.endpoint, self.bucket_name)

    async def upload_video(
        self,
        local_path: str,
        user_id: int,
        stage_id: int,
    ) -> dict:
        """上传视频到 OSS"""
        if not os.path.exists(local_path):
            return {"success": False, "error": f"文件不存在: {local_path}"}

        key = self._build_key(user_id, stage_id)

        try:
            bucket = self._get_bucket()
            file_size = os.path.getsize(local_path)
            log.info(f"OSS 上传开始: {local_path} → {key} ({file_size} bytes)")

            import asyncio
            loop = asyncio.get_event_loop()
            with open(local_path, "rb") as f:
                result = await loop.run_in_executor(
                    None,
                    lambda: bucket.put_object(key, f),
                )

            etag = result.etag.strip('"') if result and result.etag else ""
            url = self._build_url(key)
            log.info(f"OSS 上传完成: {url} (etag={etag})")
            return {"success": True, "url": url, "oss_key": key, "etag": etag}

        except Exception as e:
            log.error(f"OSS 上传失败: {e}")
            return {"success": False, "error": str(e)}


# 全局实例
oss_uploader = OSSUploader()
