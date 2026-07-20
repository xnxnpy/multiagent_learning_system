"""讯飞 ASR（语音识别）WebSocket 客户端"""
import json
import base64
import hashlib
import hmac
import ssl
import struct
from datetime import datetime
from urllib.parse import urlencode, urlparse
import websockets
from app.core.config import settings
from app.core.logger import log


class XunfeiASRClient:
    """讯飞流式语音识别 WebSocket 客户端"""

    FRAME_SIZE = 4096  # 每帧音频大小（字节）

    def __init__(
        self,
        app_id: str = None,
        api_key: str = None,
        api_secret: str = None,
        ws_url: str = None,
    ):
        self.app_id = app_id or settings.XUNFEI_APP_ID
        self.api_key = api_key or settings.XUNFEI_API_KEY
        self.api_secret = api_secret or settings.XUNFEI_API_SECRET
        self.ws_url = ws_url or getattr(settings, 'XUNFEI_ASR_WS_URL', 'wss://iat-api.xfyun.cn/v2/iat')

    def _build_auth_url(self) -> str:
        """构建带鉴权参数的 WebSocket URL（复用 TTS 鉴权模式）"""
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

    def _parse_result(self, data: dict) -> str:
        """从识别结果中提取文本"""
        result = data.get("data", {}).get("result", {})
        ws_list = result.get("ws", [])
        text_parts = []
        for ws in ws_list:
            for cw in ws.get("cw", []):
                text_parts.append(cw.get("w", ""))
        return "".join(text_parts)

    async def recognize(self, audio_data: bytes) -> str:
        """将音频数据转为文本（PCM 16bit 16kHz 单声道）

        Args:
            audio_data: PCM 音频数据（16bit, 16kHz, mono）
        Returns:
            识别出的文本
        """
        if not audio_data:
            log.warning("ASR 输入音频为空")
            return ""

        url = self._build_auth_url()
        log.info(f"讯飞 ASR 开始识别，音频大小: {len(audio_data)} bytes")

        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            result_text = ""

            async with websockets.connect(
                url,
                ssl=ssl_context,
                ping_interval=10,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                # 将音频按帧切分
                frames = []
                for i in range(0, len(audio_data), self.FRAME_SIZE):
                    frames.append(audio_data[i:i + self.FRAME_SIZE])

                if not frames:
                    return ""

                # 逐帧发送
                for idx, chunk in enumerate(frames):
                    is_first = (idx == 0)
                    is_last = (idx == len(frames) - 1)

                    frame = {
                        "data": {
                            "status": 0 if is_first else (2 if is_last else 1),
                            "format": "audio/L16;rate=16000",
                            "encoding": "raw",
                            "audio": base64.b64encode(chunk).decode("utf-8"),
                        }
                    }
                    # 第一帧带 common + business
                    if is_first:
                        frame["common"] = {"app_id": self.app_id}
                        frame["business"] = {
                            "language": "zh_cn",
                            "domain": "iat",
                            "accent": "mandarin",
                            "vad_eos": 3000,
                        }
                    await ws.send(json.dumps(frame))

                # 接收识别结果
                while True:
                    try:
                        resp = await ws.recv()
                    except websockets.exceptions.ConnectionClosed:
                        break

                    data = json.loads(resp)
                    code = data.get("code", -1)
                    if code != 0:
                        error_msg = data.get("message", "未知错误")
                        log.error(f"讯飞 ASR 错误: code={code}, message={error_msg}")
                        raise RuntimeError(f"讯飞 ASR 识别失败: {error_msg}")

                    # 拼接识别结果
                    part = self._parse_result(data)
                    if part:
                        result_text += part

                    # 检查是否结束
                    status = data.get("data", {}).get("status")
                    if status == 2:
                        break

            log.info(f"讯飞 ASR 识别完成: {result_text[:100]}...")
            return result_text.strip()

        except Exception as e:
            log.error(f"讯飞 ASR 调用失败: {e}")
            raise


# 全局实例
xunfei_asr = XunfeiASRClient()
