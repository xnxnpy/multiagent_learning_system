# -*- coding: utf-8 -*-
"""测试图片生成 API - Z-Image-Turbo / Qwen-Image / SDXL"""
import asyncio
import httpx

APP_ID = "e2d4d393"
API_KEY = "f4c1726de628f7ba6f1699ca0e11bd6c"
API_SECRET = "YTI0OTE0Yzc3NTEwZmVmNzdhNjQzYzIw"

TEST_PROMPT = "a cute cat sitting on a desk, flat design illustration"


async def run_image_model_test(domain, model_name):
    url = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}:{API_SECRET}",
    }
    payload = {
        "header": {"app_id": APP_ID, "uid": "test_user", "patch_id": ["1"]},
        "parameter": {
            "chat": {
                "domain": domain,
                "width": 1024,
                "height": 1024,
                "seed": 42,
                "num_inference_steps": 20,
                "guidance_scale": 5.0,
                "scheduler": "Euler",
            }
        },
        "payload": {
            "message": {"text": [{"role": "user", "content": TEST_PROMPT}]},
            "negative_prompts": {"text": "blurry, low quality, distorted"},
        },
    }

    print(f"[{model_name}] domain={domain} ...")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            result = resp.json()
            code = result.get("header", {}).get("code")
            msg = result.get("header", {}).get("message", "")
            if code == 0:
                texts = result.get("payload", {}).get("choices", {}).get("text", [])
                img_len = len(texts[0].get("content", "")) if texts else 0
                print(f"  OK - code={code}, image_base64_len={img_len}")
            else:
                print(f"  FAIL - code={code}, msg={msg}")
    except Exception as e:
        print(f"  ERROR - {e}")


async def main():
    await run_image_model_test("xopzimageturbo", "Z-Image-Turbo")
    # await run_image_model_test("xopqwentti20b", "Qwen-Image (baseline)")
    # await run_image_model_test("xssdxl", "StableDiffusion_XL_Base_1")


if __name__ == "__main__":
    asyncio.run(main())
