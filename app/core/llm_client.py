import json
import hashlib
import base64
import hmac
import time
import asyncio
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
from typing import List, Dict, Optional, Any
from enum import Enum
from app.core.config import settings
from app.core.logger import log


class XunfeiModel(Enum):
    """讯飞星火模型枚举"""
    LITE = "lite"
    PRO = "generalv3"
    PRO_128K = "pro-128k"
    ULTRA = "4.0Ultra"
    MAX = "generalv3.5"
    X1 = "spark-x"          # X1.5
    X2 = "spark-x"          # X2
    X2_FLASH = "spark-x"    # X2-Flash
    QWEN36 = "xopqwen36v35b"   # Qwen3.6-35B-A3B (MaaS WebSocket)
    QWEN35 = "xopqwen35v35b"   # Qwen3.5-35B-A3B (MaaS WebSocket)
    QWEN35_2B = "xop35qwen2b"  # Qwen3.5-2B (MaaS WebSocket)


# HTTP API 模型配置
HTTP_MODEL_CONFIGS = {
    XunfeiModel.LITE: {
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "model": "lite",
        "max_tokens": 4096,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_LITE"
    },
    XunfeiModel.PRO: {
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "model": "generalv3",
        "max_tokens": 8192,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_PRO"
    },
    XunfeiModel.PRO_128K: {
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "model": "pro-128k",
        "max_tokens": 131072,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_PRO_128K"
    },
    XunfeiModel.ULTRA: {
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "model": "4.0Ultra",
        "max_tokens": 32768,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_ULTRA"
    },
    XunfeiModel.MAX: {
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "model": "generalv3.5",
        "max_tokens": 8192,
        "temperature": 0.5,
        # MAX 模型已停用：无独立 APIPassword 配置，需要时在 config.py 补 XUNFEI_API_PASSWORD_MAX
        "password_key": "XUNFEI_API_PASSWORD_PRO"
    },
    XunfeiModel.X1: {
        "endpoint": "https://spark-api-open.xf-yun.com/v2/chat/completions",
        "model": "spark-x",
        "max_tokens": 65535,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_X1"
    },
    XunfeiModel.X2: {
        "endpoint": "https://spark-api-open.xf-yun.com/x2/chat/completions",
        "model": "spark-x",
        "max_tokens": 131072,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_X2"
    },
    XunfeiModel.X2_FLASH: {
        "endpoint": "https://spark-api-open.xf-yun.com/agent/v1/chat/completions",
        "model": "spark-x",
        "max_tokens": 262144,
        "temperature": 0.5,
        "password_key": "XUNFEI_API_PASSWORD_X2_FLASH"
    }
}


# WebSocket API 模型配置
WS_MODEL_CONFIGS = {
    XunfeiModel.LITE: {
        "host": "spark-api.xf-yun.com",
        "path": "/v1.1/chat",
        "domain": "lite",
    },
    XunfeiModel.PRO: {
        "host": "spark-api.xf-yun.com",
        "path": "/v3.1/chat",
        "domain": "generalv3",
    },
    XunfeiModel.PRO_128K: {
        "host": "spark-api.xf-yun.com",
        "path": "/chat/pro-128k",
        "domain": "pro-128k",
    },
    XunfeiModel.ULTRA: {
        "host": "spark-api.xf-yun.com",
        "path": "/v4.0/chat",
        "domain": "4.0Ultra",
    },
    XunfeiModel.MAX: {
        "host": "spark-api.xf-yun.com",
        "path": "/v3.5/chat",
        "domain": "generalv3.5",
    },
    XunfeiModel.X1: {
        "host": "spark-api.xf-yun.com",
        "path": "/v1/x1",
        "domain": "spark-x",
    },
    XunfeiModel.X2: {
        "host": "spark-api.xf-yun.com",
        "path": "/x2",
        "domain": "spark-x",
    },
    XunfeiModel.X2_FLASH: {
        "host": "spark-api.xf-yun.com",
        "path": "/agent/v1/chat",
        "domain": "general",
    },
    XunfeiModel.QWEN36: {
        "host": "maas-api.cn-huabei-1.xf-yun.com",
        "path": "/v1.1/chat",
        "domain": "xopqwen36v35b",
    },
    XunfeiModel.QWEN35: {
        "host": "maas-api.cn-huabei-1.xf-yun.com",
        "path": "/v1.1/chat",
        "domain": "xopqwen35v35b",
    },
    XunfeiModel.QWEN35_2B: {
        "host": "maas-api.cn-huabei-1.xf-yun.com",
        "path": "/v1.1/chat",
        "domain": "xop35qwen2b",
    },
}


class XunfeiLLM:
    """讯飞星火 API 客户端"""

    # Lite 模型并发限制为 2（讯飞 Lite QPS 限制约 2-5）
    MAX_CONCURRENT = 2

    def __init__(self):
        self.app_id = settings.XUNFEI_APP_ID
        self.api_key = settings.XUNFEI_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.default_model = self._parse_model(settings.XUNFEI_MODEL)
        self.reasoning_model = self._parse_model(settings.XUNFEI_REASONING_MODEL)
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        self._last_request_time = 0.0
        self._min_interval = 1.0  # 最小请求间隔（秒），防 QPS 超限

    def _parse_model(self, model_str: str) -> XunfeiModel:
        """解析模型名称"""
        model_mapping = {
            "lite": XunfeiModel.LITE,
            "pro": XunfeiModel.PRO,
            "pro-128k": XunfeiModel.PRO_128K,
            "ultra": XunfeiModel.ULTRA,
            "max": XunfeiModel.MAX,
            "x1": XunfeiModel.X1,
            "x1.5": XunfeiModel.X1,
            "x2": XunfeiModel.X2,
            "x2-flash": XunfeiModel.X2_FLASH,
            "flash": XunfeiModel.X2_FLASH,
            "qwen36": XunfeiModel.QWEN36,
            "qwen35": XunfeiModel.QWEN35,
            "qwen35_2b": XunfeiModel.QWEN35_2B,
        }
        return model_mapping.get(model_str.lower(), XunfeiModel.PRO)

    def _get_http_config(self, model: Optional[XunfeiModel] = None) -> Dict[str, Any]:
        """获取 HTTP API 模型配置"""
        model_to_use = model or self.default_model
        return HTTP_MODEL_CONFIGS.get(model_to_use, HTTP_MODEL_CONFIGS[XunfeiModel.PRO])

    def _get_ws_config(self, model: Optional[XunfeiModel] = None) -> Dict[str, Any]:
        """获取 WebSocket API 模型配置"""
        model_to_use = model or self.default_model
        return WS_MODEL_CONFIGS.get(model_to_use, WS_MODEL_CONFIGS[XunfeiModel.PRO])

    def _get_api_password(self, model: XunfeiModel) -> str:
        """根据模型获取对应的 API_PASSWORD"""
        config = self._get_http_config(model)
        password_key = config.get("password_key", "XUNFEI_API_PASSWORD_PRO")
        return getattr(settings, password_key, "")

    def _get_http_headers(self, model: XunfeiModel) -> Dict[str, str]:
        """HTTP API 请求头部（根据模型使用对应的密码）"""
        api_password = self._get_api_password(model)
        return {
            "Authorization": f"Bearer {api_password}",
            "Content-Type": "application/json"
        }

    def _build_http_body(
        self,
        messages: List[Dict[str, str]],
        model_config: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """构建 HTTP API 请求体"""
        return {
            "model": model_config["model"],
            "messages": messages,
            "temperature": temperature or model_config["temperature"],
            "max_tokens": max_tokens or model_config["max_tokens"]
        }

    def _generate_ws_url(self, ws_config: Dict[str, Any]) -> str:
        """生成 WebSocket 鉴权 URL（HMAC-SHA256 签名）"""
        cur_time = datetime.now()
        date_str = format_date_time(mktime(cur_time.timetuple()))
        
        host = ws_config['host']
        path = ws_config['path']
        tmp = f"host: {host}\ndate: {date_str}\nGET {path} HTTP/1.1"
        
        tmp_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            tmp.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature = base64.b64encode(tmp_sha).decode('utf-8')
        
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        
        from urllib.parse import urlencode
        v = {
            "authorization": authorization,
            "date": date_str,
            "host": host
        }
        
        return f"wss://{host}{path}?" + urlencode(v)

    def _build_ws_body(
        self,
        messages: List[Dict[str, str]],
        ws_config: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """构建 WebSocket 请求体"""
        return {
            "header": {
                "app_id": self.app_id,
                "uid": "ai_learning_user"
            },
            "parameter": {
                "chat": {
                    "domain": ws_config["domain"],
                    "temperature": temperature or 0.5,
                    "max_tokens": max_tokens or 4096
                }
            },
            "payload": {
                "message": {
                    "text": messages
                }
            }
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[XunfeiModel] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """HTTP API 调用（带并发控制和重试）"""
        model_to_use = model or self.default_model
        api_password = self._get_api_password(model_to_use)

        if not api_password:
            log.error(f"模型 {model_to_use.name} 的 API_PASSWORD 未配置！当前使用模拟数据，无法生成真实内容。请在 .env 中设置 XUNFEI_API_PASSWORD_LITE 等变量。")
            return self._mock_response(messages)

        import aiohttp
        model_config = self._get_http_config(model_to_use)
        url = model_config["endpoint"]
        body = self._build_http_body(messages, model_config, temperature, max_tokens)
        headers = self._get_http_headers(model_to_use)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    # 请求间隔控制，防 QPS 超限
                    now = time.time()
                    elapsed = now - self._last_request_time
                    if elapsed < self._min_interval:
                        await asyncio.sleep(self._min_interval - elapsed)
                    self._last_request_time = time.time()

                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            headers=headers,
                            json=body,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            if response.status == 429 or response.status >= 500:
                                error_text = await response.text()
                                # QPS 超限 / 并发超限 / 服务端错误 → 重试
                                is_qps = ("Qps" in error_text or "Concurrency" in error_text
                                          or "11202" in error_text or "11203" in error_text
                                          or response.status == 429)
                                if is_qps:
                                    # QPS 超限：给更长的等待时间
                                    wait = min(3 * (2 ** attempt), 30)
                                    log.warning(f"QPS/并发超限 ({response.status})，{wait}s 后重试 (第{attempt+1}/{max_retries}次)")
                                else:
                                    wait = min(2 ** attempt, 16)
                                    log.warning(f"LLM 请求失败 ({response.status})，{wait}s 后重试 (第{attempt+1}次): {error_text[:200]}")
                                await asyncio.sleep(wait)
                                continue

                            if response.status != 200:
                                error_text = await response.text()
                                log.error(f"讯飞星火 HTTP API 调用失败: {response.status}, {error_text}，使用模拟数据")
                                return self._mock_response(messages)

                            data = await response.json()
                            log.debug(f"讯飞星火 API 响应: {json.dumps(data, ensure_ascii=False)}")

                            choices = data.get("choices", [])
                            if choices:
                                message = choices[0].get("message", {})
                                return message.get("content", "")
                            return ""

            except asyncio.TimeoutError:
                log.warning(f"LLM 请求超时 (第{attempt+1}次)")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return self._mock_response(messages)
            except Exception as e:
                log.error(f"讯飞星火 API 调用异常: {e}")
                return self._mock_response(messages)

        log.error(f"LLM 请求在 {max_retries} 次重试后仍失败，使用模拟数据")
        return self._mock_response(messages)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[XunfeiModel] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """HTTP API 流式调用"""
        model_to_use = model or self.default_model
        api_password = self._get_api_password(model_to_use)

        if not api_password:
            log.warning(f"模型 {model_to_use.name} 需要配置 API_PASSWORD，使用模拟数据")
            async for chunk in self._mock_stream_response(messages):
                yield chunk
            return

        import aiohttp
        model_config = self._get_http_config(model_to_use)
        url = model_config["endpoint"]
        body = self._build_http_body(messages, model_config, temperature, max_tokens)
        body["stream"] = True
        headers = self._get_http_headers(model_to_use)

        try:
            async with self._semaphore:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        headers=headers,
                        json=body,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            log.error(f"讯飞星火 HTTP API 流式调用失败: {response.status}, {error_text}")
                            async for chunk in self._mock_stream_response(messages):
                                yield chunk
                            return

                        # HTTP 流式解析：用 buffer 处理不规则 chunks
                        buffer = ""
                        got_content = False
                        async for raw_chunk in response.content:
                            buffer += raw_chunk.decode('utf-8', errors='ignore')
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                if not line or not line.startswith('data: '):
                                    continue
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    if not got_content:
                                        log.warning("HTTP 流式结束但无内容，回退模拟数据")
                                        async for chunk in self._mock_stream_response(messages):
                                            yield chunk
                                    return
                                try:
                                    data = json.loads(data_str)
                                    choices = data.get('choices', [])
                                    if choices:
                                        delta = choices[0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            got_content = True
                                            yield content
                                except json.JSONDecodeError:
                                    continue

                        if not got_content:
                            log.warning("HTTP 流式无内容，回退模拟数据")
                            async for chunk in self._mock_stream_response(messages):
                                yield chunk

        except Exception as e:
            log.error(f"讯飞星火 API 流式调用异常: {e}")
            async for chunk in self._mock_stream_response(messages):
                yield chunk

    async def chat_websocket(
        self,
        messages: List[Dict[str, str]],
        model: Optional[XunfeiModel] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """WebSocket 调用"""
        if not self.api_key or not self.api_secret:
            log.warning("讯飞星火 WebSocket 需要配置 API_KEY 和 API_SECRET，使用模拟数据")
            return self._mock_response(messages)

        import aiohttp
        ws_config = self._get_ws_config(model)
        url = self._generate_ws_url(ws_config)
        body = self._build_ws_body(messages, ws_config, temperature, max_tokens)

        full_response = ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    url,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as ws:
                    await ws.send_json(body)

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            choices = data.get("payload", {}).get("choices", {})
                            text_list = choices.get("text", [])
                            if text_list:
                                content = text_list[0].get("content", "")
                                full_response += content
                            if choices.get("status") == 2:
                                break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            log.error(f"WebSocket 错误: {msg.data}")
                            break

        except Exception as e:
            log.error(f"讯飞星火 WebSocket 调用异常: {e}")
            return self._mock_response(messages)

        return full_response

    async def chat_websocket_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[XunfeiModel] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """WebSocket 流式调用"""
        if not self.api_key or not self.api_secret:
            log.warning("讯飞星火 WebSocket 需要配置 API_KEY 和 API_SECRET，使用模拟数据")
            async for chunk in self._mock_stream_response(messages):
                yield chunk
            return

        import aiohttp
        ws_config = self._get_ws_config(model)
        url = self._generate_ws_url(ws_config)
        body = self._build_ws_body(messages, ws_config, temperature, max_tokens)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    url,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as ws:
                    await ws.send_json(body)

                    got_content = False
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            header = data.get("header") or {}
                            code = header.get("code")
                            if code not in (None, 0):
                                log.error(f"讯飞 WS 错误码 {code}: {header.get('message', '')}")
                                break
                            choices = data.get("payload", {}).get("choices", {})
                            text_list = choices.get("text", [])
                            if text_list:
                                content = text_list[0].get("content", "")
                                if content:
                                    got_content = True
                                    yield content
                            if choices.get("status") == 2:
                                break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            log.error(f"WebSocket 流式错误: {msg.data}")
                            break

                    if not got_content:
                        log.warning("讯飞 WS 流式无内容，回退 HTTP 流式")
                        async for chunk in self.chat_stream(
                            messages, model=model, temperature=temperature, max_tokens=max_tokens
                        ):
                            yield chunk
                        return

        except Exception as e:
            log.error(f"讯飞星火 WebSocket 流式调用异常: {e}，回退 HTTP 流式")
            async for chunk in self.chat_stream(
                messages, model=model, temperature=temperature, max_tokens=max_tokens
            ):
                yield chunk

    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        """生成模拟响应（API 不可用时的降级数据）"""
        last_message = messages[-1]["content"] if messages else ""

        if any(keyword in last_message for keyword in ["代码", "编程", "Python", "function", "code"]):
            return json.dumps({
                "title": "Python 基础示例代码",
                "description": "以下是一个常用的 Python 基础代码示例，包含函数定义和常用操作。",
                "code": "# Python 基础示例\ndef calculate_average(numbers):\n    \"\"\"计算列表的平均值\"\"\"\n    if not numbers:\n        return 0\n    return sum(numbers) / len(numbers)\n\n# 测试\nnums = [85, 90, 78, 92, 88]\nresult = calculate_average(nums)\nprint(f\"平均值: {result:.2f}\")",
                "input_example": "[85, 90, 78, 92, 88]",
                "expected_output": "86.60",
                "test_cases": [
                    {"input": "[1, 2, 3]", "expected": "2.0"},
                    {"input": "[10, 20, 30, 40]", "expected": "25.0"}
                ],
                "difficulty": "easy",
                "tags": ["Python", "函数", "基础"]
            }, ensure_ascii=False)

        if any(keyword in last_message for keyword in ["视频脚本", "配图", "思维导图", "多模态"]):
            return json.dumps({
                "video_script": {
                    "title": "学习主题教学视频",
                    "scenes": [
                        {"visual": "开场介绍", "narration": "欢迎来到本节课程", "duration": "30秒"},
                        {"visual": "核心概念讲解", "narration": "让我们来了解核心知识点", "duration": "2分钟"},
                        {"visual": "代码演示", "narration": "接下来通过实例演示", "duration": "3分钟"},
                        {"visual": "总结回顾", "narration": "本节重点回顾", "duration": "1分钟"}
                    ]
                },
                "mindmap": {"title": "知识图谱", "nodes": ["核心概念", "基础语法", "实践应用"]},
                "mindmap_html": "<html><body style='font-family:sans-serif;padding:20px'><h2>知识图谱</h2><ul><li>核心概念</li><li>基础语法</li><li>实践应用</li></ul></body></html>"
            }, ensure_ascii=False)

        if any(keyword in last_message for keyword in ["题目", "练习", "选择题"]):
            return json.dumps({
                "questions": [
                    {
                        "question_id": 1,
                        "type": "choice",
                        "difficulty": "easy",
                        "question": "以下哪个是 Python 中定义函数的关键字？",
                        "options": ["function", "def", "func", "define"],
                        "answer": "def",
                        "score": 10
                    },
                    {
                        "question_id": 2,
                        "type": "choice",
                        "difficulty": "easy",
                        "question": "Python 中用于输出内容到控制台的函数是？",
                        "options": ["echo()", "console.log()", "print()", "output()"],
                        "answer": "print()",
                        "score": 10
                    },
                    {
                        "question_id": 3,
                        "type": "blank",
                        "difficulty": "medium",
                        "question": "Python 中使用 ______ 关键字定义一个匿名函数",
                        "answer": "lambda",
                        "score": 10
                    },
                    {
                        "question_id": 4,
                        "type": "code",
                        "difficulty": "medium",
                        "question": "编写一个 Python 函数，接收一个列表，返回其中所有偶数的平方和",
                        "answer": "def even_square_sum(nums):\n    return sum(x**2 for x in nums if x % 2 == 0)",
                        "test_cases": [
                            {"input": "[1, 2, 3, 4]", "expected": "20"},
                            {"input": "[2, 4, 6]", "expected": "56"}
                        ],
                        "score": 20
                    },
                    {
                        "question_id": 5,
                        "type": "code",
                        "difficulty": "hard",
                        "question": "编写一个 Python 函数，判断一个字符串是否是回文串",
                        "answer": "def is_palindrome(s):\n    return s == s[::-1]",
                        "test_cases": [
                            {"input": "racecar", "expected": "True"},
                            {"input": "hello", "expected": "False"}
                        ],
                        "score": 20
                    }
                ]
            }, ensure_ascii=False)

        if any(keyword in last_message for keyword in ["循环", "知识点", "文档"]):
            return "# 学习文档\n\n## 核心知识点\n\n1. **基础概念**：理解基本定义和用途\n2. **语法要点**：掌握关键语法结构\n3. **实践应用**：通过实例加深理解\n\n## 详细说明\n\n```python\n# 示例代码\nfor i in range(5):\n    print(f'第 {i+1} 次循环')\n```\n\n## 总结\n\n本节介绍了基础知识的核心要点，建议多加练习。"

        if any(keyword in last_message for keyword in ["学习路径", "规划"]):
            return json.dumps({
                "stages": [
                    {"stage_id": 1, "title": "基础入门", "description": "学习基本概念和语法"},
                    {"stage_id": 2, "title": "进阶提高", "description": "深入学习核心特性"},
                    {"stage_id": 3, "title": "实战应用", "description": "通过项目巩固知识"}
                ]
            }, ensure_ascii=False)

        if any(keyword in last_message for keyword in ["专业", "major"]):
            return json.dumps({
                "major": "计算机科学", "grade": "大二",
                "goal": "Python 编程学习", "level": "初级",
                "interests": ["编程", "算法"]
            }, ensure_ascii=False)

        return json.dumps({"message": "请描述您的学习背景"})

    async def _mock_stream_response(self, messages: List[Dict[str, str]]):
        """生成模拟流式响应"""
        import asyncio
        mock_result = self._mock_response(messages)
        for i in range(0, len(mock_result), 10):
            yield mock_result[i:i+10]
            await asyncio.sleep(0.05)


# 创建全局实例
xunfei_llm = XunfeiLLM()
