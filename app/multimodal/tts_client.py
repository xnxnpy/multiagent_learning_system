"""讯飞 TTS WebSocket 客户端"""
import json
import time
import base64
import hashlib
import hmac
import ssl
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode, urlparse
import websockets
from app.core.config import settings
from app.core.logger import log


class XunfeiTTSClient:
    """讯飞语音合成 WebSocket 客户端"""

    def __init__(
        self,
        app_id: str = None,
        api_key: str = None,
        api_secret: str = None,
        ws_url: str = None,
    ):
        self.app_id = app_id or settings.XUNFEI_TTS_APP_ID
        self.api_key = api_key or settings.XUNFEI_API_KEY
        self.api_secret = api_secret or settings.XUNFEI_API_SECRET
        self.ws_url = ws_url or settings.XUNFEI_TTS_WS_URL

    def _build_auth_url(self) -> str:
        """构建带鉴权参数的 WebSocket URL"""
        parsed = urlparse(self.ws_url)
        host = parsed.hostname
        path = parsed.path

        now = datetime.utcnow()
        date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        params = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
        return f"{self.ws_url}?{urlencode(params)}"

    def _build_payload(
        self,
        text: str,
        voice: str = "x4_yezi",
        speed: int = 50,
        volume: int = 50,
    ) -> dict:
        """构建 TTS 请求 payload"""
        text_bytes = text.encode("utf-8")
        text_base64 = base64.b64encode(text_bytes).decode("utf-8")

        return {
            "common": {"app_id": self.app_id},
            "business": {
                "aue": "lame",
                "sfl": 1,
                "auf": "audio/L16;rate=16000",
                "vcn": voice,
                "speed": speed,
                "volume": volume,
                "tte": "UTF8",
            },
            "data": {
                "status": 2,
                "text": text_base64,
            },
        }

    async def synthesize(
        self,
        text: str,
        voice: str = "x4_yezi",
        speed: int = 50,
        volume: int = 50,
    ) -> bytes:
        """将文本转为音频，返回音频 bytes (opus 编码)"""
        if not text or not text.strip():
            log.warning("TTS 输入文本为空，返回空 bytes")
            return b""

        url = self._build_auth_url()
        payload = self._build_payload(text, voice=voice, speed=speed, volume=volume)
        audio_chunks = []

        log.info(f"讯飞 TTS 开始合成，文本长度: {len(text)} 字符")

        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            async with websockets.connect(
                url,
                ssl=ssl_context,
                ping_interval=10,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                await ws.send(json.dumps(payload))

                while True:
                    try:
                        resp = await ws.recv()
                    except websockets.exceptions.ConnectionClosed:
                        break

                    data = json.loads(resp)
                    code = data.get("code", -1)

                    if code != 0:
                        error_msg = data.get("message", "未知错误")
                        log.error(f"讯飞 TTS 错误: code={code}, message={error_msg}")
                        raise RuntimeError(f"讯飞 TTS 合成失败: {error_msg}")

                    audio = data.get("data", {}).get("audio")
                    status = data.get("data", {}).get("status")

                    if audio:
                        audio_chunks.append(base64.b64decode(audio))

                    if status == 2:
                        break

            result = b"".join(audio_chunks)
            log.info(f"讯飞 TTS 合成完成，音频大小: {len(result)} bytes")
            return result

        except Exception as e:
            log.error(f"讯飞 TTS 调用失败: {e}")
            raise


# 全局实例
xunfei_tts = XunfeiTTSClient()
