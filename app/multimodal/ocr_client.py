"""讯飞 OCR（通用文字识别 intsig）HTTP 客户端

用于辅导场景中识别图片中的题目文字，将图片转为文本后传给 TutorAgent。
TutorAgent 使用的大模型不一定支持多模态，因此图片需先经 OCR 转为纯文本。

接口文档: https://www.xfyun.cn/doc/words/universal-character-recognition/API.html
请求地址: https://api.xf-yun.com/v1/private/hh_ocr_recognize_doc
支持语种: 中、日、韩、英、德、法等 52 种语言
鉴权方式: hmac-sha256 签名（URL query 参数）
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode, urlparse

import httpx

from app.core.config import settings
from app.core.logger import log


class XunfeiOCRClient:
    """讯飞通用文字识别 intsig HTTP 客户端

    鉴权流程:
        1. signature_origin = "host: {host}\\ndate: {date}\\nPOST {path} HTTP/1.1"
        2. signature = base64(hmac-sha256(api_secret, signature_origin))
        3. authorization_origin = 'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        4. authorization = base64(authorization_origin)
        5. URL 追加 ?authorization={authorization}&host={host}&date={date}
    """

    def __init__(
        self,
        app_id: str = None,
        api_key: str = None,
        api_secret: str = None,
        api_url: str = None,
    ):
        self.app_id = app_id or settings.XUNFEI_APP_ID
        self.api_key = api_key or settings.XUNFEI_API_KEY
        self.api_secret = api_secret or settings.XUNFEI_API_SECRET
        self.api_url = api_url or getattr(
            settings, "XUNFEI_OCR_URL", "https://api.xf-yun.com/v1/private/hh_ocr_recognize_doc"
        )

    def _build_auth_url(self) -> str:
        """构建带鉴权参数的请求 URL"""
        parsed = urlparse(self.api_url)
        host = parsed.hostname
        path = parsed.path

        # RFC1123 格式时间（UTC）
        now = datetime.utcnow()
        date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # 签名原始字段
        signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")

        # authorization
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(
            authorization_origin.encode("utf-8")
        ).decode("utf-8")

        params = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
        return f"{self.api_url}?{urlencode(params)}"

    async def recognize(self, image_data: bytes) -> str:
        """识别图片中的文字

        Args:
            image_data: 图片二进制数据（支持 jpg/jpeg/png/bmp）

        Returns:
            识别出的文本内容
        """
        if not image_data:
            log.warning("OCR 输入图片为空")
            return ""

        # base64 编码图片
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # 构建请求体（intsig 版结构）
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 3,
            },
            "parameter": {
                "hh_ocr_recognize_doc": {
                    "recognizeDocumentRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json",
                    },
                }
            },
            "payload": {
                "image": {
                    "encoding": "jpg",
                    "image": image_b64,
                    "status": 3,
                }
            },
        }

        url = self._build_auth_url()
        log.info(f"讯飞 OCR(intsig) 开始识别，图片大小: {len(image_data)} bytes")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json=request_body,
                    headers={"Content-Type": "application/json"},
                )
                result = resp.json()

            # 检查会话是否成功
            code = result.get("header", {}).get("code")
            if code != 0:
                error_msg = result.get("header", {}).get("message", "未知错误")
                log.error(f"讯飞 OCR 错误: code={code}, message={error_msg}")
                raise RuntimeError(f"讯飞 OCR 识别失败: {error_msg}")

            # text 字段是 base64 编码的 JSON
            text_b64 = (
                result.get("payload", {})
                .get("recognizeDocumentRes", {})
                .get("text", "")
            )
            if not text_b64:
                log.warning("讯飞 OCR 返回结果为空")
                return ""

            decoded = base64.b64decode(text_b64).decode("utf-8")
            ocr_data = json.loads(decoded)

            # 优先使用 whole_text 全文，兜底逐行拼接
            recognized_text = ocr_data.get("whole_text", "")
            if not recognized_text:
                text_parts = []
                for line in ocr_data.get("lines", []):
                    line_text = line.get("text", "")
                    if line_text:
                        text_parts.append(line_text)
                recognized_text = "\n".join(text_parts)

            log.info(f"讯飞 OCR(intsig) 识别完成: {recognized_text[:100]}...")
            return recognized_text.strip()

        except httpx.HTTPError as e:
            log.error(f"讯飞 OCR 网络请求失败: {e}")
            raise RuntimeError(f"OCR 网络请求失败: {e}")
        except Exception as e:
            log.error(f"讯飞 OCR 调用失败: {e}")
            raise


# 全局实例
xunfei_ocr = XunfeiOCRClient()
