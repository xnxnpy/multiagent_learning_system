from typing import List, Dict, Any, Optional
import httpx
import json
from app.core.logger import log
from app.core.config import settings


class ImageGenerator:
    """图片生成器，支持多种 AI 绘图 API"""

    def __init__(self, provider: str = "z_image_turbo"):
        self.provider = provider

    async def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成单张图片

        Args:
            prompt: 图片生成提示词
            **kwargs: 其他参数（size, style 等）

        Returns:
            包含图片 URL 或 base64 的字典
        """
        if self.provider == "stable_diffusion":
            return await self._generate_with_sd(prompt, **kwargs)
        elif self.provider == "dalle":
            return await self._generate_with_dalle(prompt, **kwargs)
        elif self.provider == "qwen_image" or self.provider == "z_image_turbo":
            return await self._generate_with_qwen_image(prompt, **kwargs)
        elif self.provider == "sdxl":
            return await self._generate_with_sdxl(prompt, **kwargs)
        else:
            raise ValueError(f"不支持的图片生成提供商: {self.provider}")

    async def _generate_with_sd(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        使用 Stable Diffusion API 生成图片

        Args:
            prompt: 英文提示词
            **kwargs: SD 特定参数

        Returns:
            图片结果
        """
        log.info(f"使用 Stable Diffusion 生成图片: {prompt[:50]}...")

        api_url = kwargs.get("api_url", "http://localhost:7860/sdapi/v1/txt2img")
        negative_prompt = kwargs.get("negative_prompt", "low quality, blurry, distorted")
        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 1024)
        steps = kwargs.get("steps", 30)
        cfg_scale = kwargs.get("cfg_scale", 7.0)

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(api_url, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    image_base64 = result.get("images", [None])[0]

                    return {
                        "success": True,
                        "provider": "stable_diffusion",
                        "image_base64": image_base64,
                        "prompt": prompt,
                        "params": {
                            "width": width,
                            "height": height,
                            "steps": steps
                        }
                    }
                else:
                    log.error(f"SD API 返回错误: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API 返回状态码: {response.status_code}"
                    }

        except Exception as e:
            log.error(f"SD 图片生成失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_with_dalle(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        使用 DALL-E API 生成图片

        Args:
            prompt: 提示词
            **kwargs: DALL-E 特定参数

        Returns:
            图片结果
        """
        log.info(f"使用 DALL-E 生成图片: {prompt[:50]}...")

        size = kwargs.get("size", "1024x1024")
        api_key = kwargs.get("api_key", "")

        if not api_key:
            return {
                "success": False,
                "error": "DALL-E API Key 未配置"
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "n": 1,
            "size": size
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    image_url = result["data"][0]["url"]

                    return {
                        "success": True,
                        "provider": "dalle",
                        "image_url": image_url,
                        "prompt": prompt
                    }
                else:
                    log.error(f"DALL-E API 返回错误: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API 返回状态码: {response.status_code}"
                    }

        except Exception as e:
            log.error(f"DALL-E 图片生成失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_with_qwen_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """使用讯飞 MaaS 图片生成 API（通过 model_manager 路由模型配置）"""
        from app.core.model_manager import IMAGE_MODELS

        # 优先用 kwargs 传入的 model_key，否则用 provider 映射
        model_key = kwargs.get("model_key") or self.provider
        model_config = IMAGE_MODELS.get(model_key)
        if not model_config:
            model_config = IMAGE_MODELS.get("z_image_turbo")

        log.info(f"使用图片模型 [{model_key}] 生成: {prompt[:50]}...")

        api_url = model_config["endpoint"]
        app_id = model_config.get("app_id", "e2d4d393")
        model_id = model_config["model_id"]
        api_key = settings.XUNFEI_API_KEY
        api_secret = settings.XUNFEI_API_SECRET

        if not api_key or not api_secret:
            return {"success": False, "error": "QWEN_IMAGE_API_KEY 或 QWEN_IMAGE_API_SECRET 未配置"}

        # Bearer token 鉴权
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}:{api_secret}",
        }

        # 讯飞 MaaS 标准请求格式
        payload = {
            "header": {
                "app_id": app_id,
                "uid": "ai_learning_user",
                "patch_id": ["1"]
            },
            "parameter": {
                "chat": {
                    "domain": model_id,
                    "width": kwargs.get("width", 1024),
                    "height": kwargs.get("height", 1024),
                    "seed": kwargs.get("seed", 42),
                    "num_inference_steps": kwargs.get("steps", 20),
                    "guidance_scale": kwargs.get("guidance", 5.0),
                    "scheduler": "Euler"
                }
            },
            "payload": {
                "message": {
                    "text": [
                        {"role": "user", "content": prompt}
                    ]
                },
                "negative_prompts": {
                    "text": kwargs.get("negative_prompt", "blurry, low quality, distorted")
                }
            }
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    header = result.get("header", {})
                    code = header.get("code")
                    message = header.get("message", "")

                    if code == 0:
                        # 从响应中提取图片 base64
                        choices = result.get("payload", {}).get("choices", {})
                        texts = choices.get("text", [])
                        image_base64 = texts[0].get("content", "") if texts else ""

                        if image_base64:
                            log.info(f"图片生成成功，base64 长度: {len(image_base64)}")
                            return {
                                "success": True,
                                "provider": "z_image_turbo",
                                "image_base64": image_base64,
                                "prompt": prompt,
                                "model_id": model_id,
                            }
                        else:
                            log.error(f"API 返回成功但无图片数据: {json.dumps(result, ensure_ascii=False)[:300]}")
                            return {"success": False, "error": "API 返回成功但无图片数据"}
                    else:
                        log.error(f"图片生成 API 错误: {code} - {message}")
                        return {"success": False, "error": message, "code": code}
                else:
                    body = response.text[:300]
                    log.error(f"图片生成 HTTP 错误: {response.status_code} - {body}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            log.error(f"图片生成异常: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_with_sdxl(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """使用 StableDiffusion XL API（通过 model_manager 路由）"""
        kwargs["model_key"] = "sdxl"
        return await self._generate_with_qwen_image(prompt, **kwargs)

    async def generate_batch(self, prompts: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        批量生成图片

        Args:
            prompts: 提示词列表
            **kwargs: 其他参数

        Returns:
            图片结果列表
        """
        log.info(f"批量生成 {len(prompts)} 张图片")

        results = []
        for i, prompt in enumerate(prompts):
            log.info(f"生成第 {i+1}/{len(prompts)} 张图片")
            result = await self.generate_image(prompt, **kwargs)
            result["index"] = i
            results.append(result)

        return results


# 创建全局实例
image_generator = ImageGenerator()