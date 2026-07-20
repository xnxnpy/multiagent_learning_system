"""
统一模型管理器 - 支持多模型路由、持久化配置和运行时切换

模型分类：
1. 文本生成模型 - Agent 对话、文档生成、题目生成等
2. 图片生成模型 - 配图、思维导图背景等

使用方式：
    from app.core.model_manager import model_manager
    response = await model_manager.chat(messages, agent_name="profile")
    image = await model_manager.generate_image(prompt, task="document_illustration")
"""
import json
import time
import asyncio
import httpx
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.core.logger import log


class RateLimiter:
    """限流器 - 控制并发数和QPS"""

    def __init__(self, model_key: str, concurrency: int, qps: int):
        self.model_key = model_key
        self.concurrency = concurrency
        self.qps = qps
        self._semaphore = asyncio.Semaphore(concurrency)
        self._last_request_time = 0
        self._min_interval = 1.0 / qps if qps > 0 else 0

    async def acquire(self):
        """获取执行许可"""
        await self._semaphore.acquire()

        # QPS 限流
        if self._min_interval > 0:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

    def release(self):
        """释放执行许可"""
        self._semaphore.release()


# ═══════════════════════════════════════════
# 模型注册表（所有可用模型）+ 限流配置
# ═══════════════════════════════════════════

TEXT_MODELS = {
    "spark_lite": {
        "name": "Spark Lite",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "ws_endpoint": "wss://spark-api.xf-yun.com/v1.1/chat",
        "ws_domain": "lite",
        "model": "lite",
        "max_tokens": 8192,
        "password_key": "XUNFEI_API_PASSWORD_LITE",
        "concurrency": 5,
        "qps": 5,
    },
    "spark_pro": {
        "name": "Spark Pro",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "ws_endpoint": "wss://spark-api.xf-yun.com/v3.1/chat",
        "ws_domain": "generalv3",
        "model": "generalv3",
        "max_tokens": 8192,
        "password_key": "XUNFEI_API_PASSWORD_PRO",
        "concurrency": 999,
        "qps": 999,
    },
    "spark_pro_128k": {
        "name": "Spark Pro-128K",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "ws_endpoint": "wss://spark-api.xf-yun.com/chat/pro-128k",
        "ws_domain": "pro-128k",
        "model": "pro-128k",
        "max_tokens": 131072,
        "password_key": "XUNFEI_API_PASSWORD_PRO_128K",
        "concurrency": 999,
        "qps": 999,
    },
    "spark_ultra": {
        "name": "Spark Ultra-32K",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/v1/chat/completions",
        "ws_endpoint": "wss://spark-api.xf-yun.com/v4.0/chat",
        "ws_domain": "4.0Ultra",
        "model": "4.0Ultra",
        "max_tokens": 32768,
        "password_key": "XUNFEI_API_PASSWORD_ULTRA",
        "concurrency": 999,
        "qps": 999,
    },
    "spark_x2_flash": {
        "name": "Spark X2-Flash",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/agent/v1/chat/completions",
        "model": "spark-x",
        "max_tokens": 262144,
        "password_key": "XUNFEI_API_PASSWORD_X2_FLASH",
        "concurrency": 20,
        "qps": 20,
    },
    "spark_x2": {
        "name": "Spark X2",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/x2/chat/completions",
        "ws_endpoint": "wss://spark-api.xf-yun.com/x2",
        "ws_domain": "spark-x",
        "model": "spark-x",
        "max_tokens": 192000,
        "password_key": "XUNFEI_API_PASSWORD_X2",
        "concurrency": 20,
        "qps": 20,
    },
    "spark_x1": {
        "name": "Spark X1.5",
        "provider": "xunfei_spark",
        "endpoint": "https://spark-api-open.xf-yun.com/v2/chat/completions",
        "ws_endpoint": "wss://spark-api.xf-yun.com/v1/x1",
        "ws_domain": "spark-x",
        "model": "spark-x",
        "max_tokens": 8192,
        "password_key": "XUNFEI_API_PASSWORD_X1",
        "concurrency": 20,
        "qps": 20,
    },
    "qwen35_2b": {
        "name": "Qwen3.5-2B",
        "provider": "xunfei_maas",
        "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",
        "ws_endpoint": "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat",
        "ws_domain": "xop35qwen2b",
        "model_id": "xop35qwen2b",
        "app_id": "e2d4d393",
        "max_tokens": 32768,
        "concurrency": 100,
        "qps": 100,
    },
    "qwen3_17b": {
        "name": "Qwen3-1.7B",
        "provider": "xunfei_maas",
        "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",
        "ws_endpoint": "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat",
        "ws_domain": "xop3qwen1b7",
        "model_id": "xop3qwen1b7",
        "app_id": "e2d4d393",
        "max_tokens": 32768,
        "concurrency": 100,
        "qps": 9999,
    },
    "qwen36_multimodal": {
        "name": "Qwen3.6-35B-A3B",
        "provider": "xunfei_maas",
        "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",
        "ws_endpoint": "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat",
        "ws_domain": "xopqwen36v35b",
        "model_id": "xopqwen36v35b",
        "app_id": "e2d4d393",
        "max_tokens": 128000,
        "concurrency": 100,
        "qps": 100,
    },
    "qwen35_multimodal": {
        "name": "Qwen3.5-35B-A3B",
        "provider": "xunfei_maas",
        "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",
        "ws_endpoint": "wss://maas-api.cn-huabei-1.xf-yun.com/v1.1/chat",
        "ws_domain": "xopqwen35v35b",
        "model_id": "xopqwen35v35b",
        "app_id": "e2d4d393",
        "max_tokens": 128000,
        "concurrency": 100,
        "qps": 100,
    },
}

IMAGE_MODELS = {
    "qwen_image": {"name": "Qwen-Image", "provider": "xunfei_maas", "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti", "model_id": "xopqwentti20b", "app_id": "e2d4d393"},
    "sdxl": {"name": "StableDiffusion XL", "provider": "xunfei_maas", "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti", "model_id": "xssdxl", "app_id": "e2d4d393"},
    "z_image_turbo": {"name": "Z-Image-Turbo", "provider": "xunfei_maas", "endpoint": "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti", "model_id": "xopzimageturbo", "app_id": "e2d4d393"},
}


# ── 默认 Agent → 文本模型映射 ──
DEFAULT_AGENT_TEXT_MODELS = {
    "profile": "spark_ultra",
    "document": "spark_x2_flash",
    "question": "spark_x2_flash",
    "code": "spark_x2_flash",
    "mindmap": "spark_x2_flash",
    "knowledge_graph": "spark_x2_flash",
    "learning_path": "spark_x2_flash",
    "evaluation": "spark_ultra",
    "tutor": "spark_ultra",
    "reading_material": "spark_x2_flash",
    "glossary": "spark_x2_flash",
    "summary": "spark_x2_flash",
    "ppt_video": "spark_x2_flash",
    "resource_quality": "spark_x2_flash",
}

# ── 默认 图片任务 → 模型映射 ──
DEFAULT_IMAGE_TASK_MODELS = {
    "document_illustration": "z_image_turbo",
}

# ── TTS 音色配置 ──
TTS_VOICES = {
    "x4_xiaoyan": {"name": "讯飞小燕", "gender": "女"},
    "x4_yezi": {"name": "讯飞小露", "gender": "女"},
    "aisjiuxu": {"name": "讯飞许久", "gender": "男"},
    "aisjinger": {"name": "讯飞小婧", "gender": "女"},
    "aisbabyxu": {"name": "讯飞许小宝", "gender": "男"},
}
DEFAULT_TTS_VOICE = "x4_yezi"



class ModelManager:
    """统一模型管理器 - 支持数据库持久化和限流"""

    def __init__(self):
        self._agent_text_models = dict(DEFAULT_AGENT_TEXT_MODELS)
        self._image_task_models = dict(DEFAULT_IMAGE_TASK_MODELS)
        self._loaded = False
        self._rate_limiters: Dict[str, 'RateLimiter'] = {}

    def _get_rate_limiter(self, model_key: str) -> 'RateLimiter':
        """获取模型的限流器"""
        if model_key not in self._rate_limiters:
            model_config = TEXT_MODELS.get(model_key, {})
            concurrency = model_config.get("concurrency", 10)
            qps = model_config.get("qps", 10)
            self._rate_limiters[model_key] = RateLimiter(model_key, concurrency, qps)
        return self._rate_limiters[model_key]

    async def load_from_db(self, db):
        """从数据库加载配置（启动时调用）"""
        from app.services.config_service import ConfigService
        config_service = ConfigService(db)

        # 加载 Agent 文本模型配置
        agent_models = await config_service.get("agent_text_models")
        if agent_models:
            self._agent_text_models.update(agent_models)
            log.info(f"从数据库加载 Agent 模型配置: {len(agent_models)} 项")

        # 加载图片任务模型配置
        image_models = await config_service.get("image_task_models")
        if image_models:
            self._image_task_models.update(image_models)
            log.info(f"从数据库加载图片模型配置: {len(image_models)} 项")

        self._loaded = True

    async def save_to_db(self, db, config_type: str = None):
        """保存配置到数据库"""
        from app.services.config_service import ConfigService
        config_service = ConfigService(db)

        if config_type == "agent_text_models" or config_type is None:
            await config_service.set("agent_text_models", self._agent_text_models, "各Agent使用的文本模型配置")

        if config_type == "image_task_models" or config_type is None:
            await config_service.set("image_task_models", self._image_task_models, "图片任务使用的模型配置")

        log.info(f"模型配置已保存到数据库: {config_type or '全部'}")

    # ═══════════════════════════════════════════
    # 配置查询和修改
    # ═══════════════════════════════════════════

    def get_all_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return {
            "text_models": {k: {"name": v["name"], "provider": v["provider"]} for k, v in TEXT_MODELS.items()},
            "image_models": {k: {"name": v["name"], "provider": v["provider"], "status": v.get("status", "可用")} for k, v in IMAGE_MODELS.items()},
            "agent_text_models": {agent: {"model_key": key, "model_name": TEXT_MODELS.get(key, {}).get("name", "未知")} for agent, key in self._agent_text_models.items()},
            "image_task_models": dict(self._image_task_models),
        }

    def set_agent_text_model(self, agent_name: str, model_key: str):
        if model_key not in TEXT_MODELS:
            raise ValueError(f"文本模型 {model_key} 不存在")
        self._agent_text_models[agent_name] = model_key
        log.info(f"Agent [{agent_name}] 文本模型切换为 [{model_key}]")

    def set_image_task_model(self, task_name: str, model_key: str):
        if model_key not in IMAGE_MODELS:
            raise ValueError(f"图片模型 {model_key} 不存在")
        self._image_task_models[task_name] = model_key
        log.info(f"图片任务 [{task_name}] 模型切换为 [{model_key}]")

    # ═══════════════════════════════════════════
    # 文本生成接口
    # ═══════════════════════════════════════════

    async def chat(self, messages: List[Dict[str, str]], agent_name: str = "default", model_key: Optional[str] = None, temperature: float = 0.5, max_tokens: Optional[int] = None, max_retries: int = 3) -> str:
        """统一文本生成接口（带限流 + 重试）"""
        from app.core.llm_client import xunfei_llm
        key = model_key or self._agent_text_models.get(agent_name, "spark_lite")
        model_config = TEXT_MODELS.get(key)
        if not model_config:
            log.error(f"文本模型 {key} 不存在，使用 spark_lite 兜底")
            model_config = TEXT_MODELS["spark_lite"]
            key = "spark_lite"

        log.info(f"[{agent_name}] 文本生成 → [{key}] ({model_config['name']})")

        model_enum = self._config_to_llm_model(model_config)
        if not model_enum:
            log.error(f"模型 {model_config.get('name')} 未在 XunfeiModel 中注册")
            return self._mock_response(messages)

        rate_limiter = self._get_rate_limiter(key)
        await rate_limiter.acquire()
        try:
            last_error = None
            for attempt in range(max_retries):
                try:
                    # 有 ws_endpoint 的模型（Qwen）只有 WebSocket，用流式收集完整响应
                    if model_config.get("ws_endpoint"):
                        full_text = ""
                        async for chunk in xunfei_llm.chat_websocket_stream(messages, model=model_enum, temperature=temperature, max_tokens=max_tokens):
                            full_text += chunk
                        return full_text
                    else:
                        return await xunfei_llm.chat(messages, model=model_enum, temperature=temperature, max_tokens=max_tokens)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(1 * (attempt + 1))
            raise last_error
        finally:
            rate_limiter.release()

    async def chat_stream(self, messages, agent_name="default", model_key: Optional[str] = None,
                          temperature: float = 0.5, max_tokens: Optional[int] = None):
        """统一流式文本生成接口"""
        import json as _json
        key = model_key or self._agent_text_models.get(agent_name, "spark_lite")
        model_config = TEXT_MODELS.get(key)
        if not model_config:
            log.error(f"文本模型 {key} 不存在，使用 spark_lite 兜底")
            model_config = TEXT_MODELS["spark_lite"]
            key = "spark_lite"

        provider = model_config["provider"]
        log.info(f"[{agent_name}] 流式生成 → [{key}] ({model_config['name']})")

        rate_limiter = self._get_rate_limiter(key)
        await rate_limiter.acquire()
        try:
            if model_config.get("ws_endpoint"):
                async for chunk in self._chat_stream_ws(messages, model_config, temperature, max_tokens):
                    yield chunk
            elif provider == "xunfei_spark":
                async for chunk in self._chat_stream_spark(messages, model_config, temperature, max_tokens):
                    yield chunk
            elif provider == "xunfei_maas":
                async for chunk in self._chat_stream_maas(messages, model_config, temperature, max_tokens):
                    yield chunk
            else:
                raise ValueError(f"不支持的提供商: {provider}")
        finally:
            rate_limiter.release()

    def _config_to_llm_model(self, config: dict):
        """将 TEXT_MODELS 的 config 映射到 llm_client 的 XunfeiModel 枚举"""
        from app.core.llm_client import XunfeiModel
        model_value = config.get("model", "") or config.get("model_id", "")
        for m in XunfeiModel:
            if m.value == model_value:
                return m
        return None

    async def _chat_stream_spark(self, messages, config, temperature, max_tokens):
        """Spark HTTP 流式调用（走 llm_client）"""
        from app.core.llm_client import xunfei_llm
        model_enum = self._config_to_llm_model(config)
        if model_enum:
            async for chunk in xunfei_llm.chat_stream(messages, model=model_enum, temperature=temperature, max_tokens=max_tokens):
                yield chunk
        else:
            log.error(f"Spark 模型 {config.get('name')} 未在 XunfeiModel 中注册，跳过")

    async def _chat_stream_maas(self, messages, config, temperature, max_tokens):
        """MaaS HTTP 流式调用（走 llm_client）"""
        from app.core.llm_client import xunfei_llm
        model_enum = self._config_to_llm_model(config)
        if model_enum:
            async for chunk in xunfei_llm.chat_stream(messages, model=model_enum, temperature=temperature, max_tokens=max_tokens):
                yield chunk
        else:
            log.error(f"MaaS 模型 {config.get('name')} 未在 XunfeiModel 中注册，跳过")

    async def _chat_stream_ws(self, messages, config, temperature, max_tokens):
        """WebSocket 流式调用（MaaS Qwen 模型，走 llm_client）"""
        from app.core.llm_client import xunfei_llm
        model_enum = self._config_to_llm_model(config)
        if not model_enum:
            log.error(f"WebSocket 模型 {config.get('model_id')} 未在 XunfeiModel 中注册")
            return
        async for chunk in xunfei_llm.chat_websocket_stream(messages, model=model_enum, temperature=temperature, max_tokens=max_tokens):
            yield chunk

    # ═══════════════════════════════════════════
    # 图片生成接口
    # ═══════════════════════════════════════════

    async def generate_image(self, prompt: str, task: str = "default", model_key: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """统一图片生成接口"""
        key = model_key or self._image_task_models.get(task, "z_image_turbo")
        model_config = IMAGE_MODELS.get(key)
        if not model_config:
            return {"success": False, "error": f"图片模型 {key} 不存在"}

        if model_config.get("status") == "未配置":
            return {"success": False, "error": f"图片模型 {model_config['name']} 未配置"}

        log.info(f"图片生成 task=[{task}] → [{key}] ({model_config['name']})")
        return await self._generate_image_maas(prompt, model_config, **kwargs)

    # ═══════════════════════════════════════════
    # 内部实现
    # ═══════════════════════════════════════════

    async def _generate_image_maas(self, prompt, config, **kwargs):
        """调用讯飞 MaaS 图片生成"""
        api_key = settings.XUNFEI_API_KEY
        api_secret = settings.XUNFEI_API_SECRET

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}:{api_secret}"}
        payload = {
            "header": {"app_id": config.get("app_id", "e2d4d393"), "uid": "ai_learning_user", "patch_id": ["1"]},
            "parameter": {"chat": {"domain": config["model_id"], "width": kwargs.get("width", 1024), "height": kwargs.get("height", 1024), "seed": kwargs.get("seed", 42), "num_inference_steps": kwargs.get("steps", 20), "guidance_scale": kwargs.get("guidance", 5.0), "scheduler": "Euler"}},
            "payload": {"message": {"text": [{"role": "user", "content": prompt}]}, "negative_prompts": {"text": kwargs.get("negative_prompt", "blurry, low quality, distorted")}}
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(config["endpoint"], headers=headers, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    header = result.get("header", {})
                    if header.get("code") == 0:
                        choices = result.get("payload", {}).get("choices", {})
                        texts = choices.get("text", [])
                        image_b64 = texts[0].get("content", "") if texts else ""
                        if image_b64:
                            return {"success": True, "image_base64": image_b64, "model_id": config["model_id"]}
                    return {"success": False, "error": header.get("message", "未知错误")}
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _mock_response(self, messages):
        last_msg = messages[-1]["content"] if messages else ""
        return f"[模拟响应] 请检查 API 配置。问题：{last_msg[:50]}..."


# 全局实例
model_manager = ModelManager()


# ═══════════════════════════════════════════════════════════════
# LangChain Chat Model 封装
# ═══════════════════════════════════════════════════════════════

from langchain_core.messages import AIMessage, BaseMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatResult, ChatGenerationChunk
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun


class ModelManagerChatModel(BaseChatModel):
    """基于 model_manager 的 LangChain Chat Model

    所有调用统一走 model_manager.chat_stream() / model_manager.chat()，
    WebSocket vs HTTP 路由由 model_manager 根据 TEXT_MODELS 中的 ws_endpoint 配置决定。
    """

    agent_name: str = "tutor"

    @property
    def _llm_type(self) -> str:
        return "model-manager"

    @property
    def _identifying_params(self) -> dict:
        key = model_manager._agent_text_models.get(self.agent_name, "spark_lite")
        return {"agent_name": self.agent_name, "model_key": key}

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        import asyncio
        async def _run():
            return await self._agenerate(messages, stop=stop, run_manager=None, **kwargs)
        return asyncio.run(_run())

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        import asyncio
        async def _run():
            chunks = []
            async for chunk in self._astream(messages, stop=stop, run_manager=None, **kwargs):
                chunks.append(chunk)
            return chunks
        chunks = asyncio.run(_run())
        for chunk in chunks:
            yield chunk

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        formatted = self._convert_messages(messages)
        full_text = await model_manager.chat(messages=formatted, agent_name=self.agent_name)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=full_text))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        formatted = self._convert_messages(messages)
        async for token in model_manager.chat_stream(messages=formatted, agent_name=self.agent_name):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                await run_manager.on_llm_new_token(token, chunk=chunk)
            yield chunk

    @staticmethod
    def _convert_messages(messages):
        result = []
        for msg in messages:
            role = msg.type
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
            result.append({"role": role, "content": msg.content})
        return result
