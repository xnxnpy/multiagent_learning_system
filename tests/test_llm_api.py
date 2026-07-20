"""测试讯飞 API 调用是否正常"""
import asyncio


async def test_chat_stream():
    """测试流式调用"""
    from app.core.model_manager import model_manager

    messages = [{"role": "user", "content": "你好，请用一句话介绍自己"}]

    print("=== 测试 chat_stream (profile 模型) ===")
    try:
        chunks = []
        async for chunk in model_manager.chat_stream(messages, agent_name="profile"):
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        print(f"\n共收到 {len(chunks)} 个 chunk")
        if not chunks:
            print("[FAIL] no chunks received!")
        else:
            print("[OK] stream works")
    except Exception as e:
        print(f"[FAIL] stream error: {e}")


async def test_chat():
    """测试非流式调用"""
    from app.core.model_manager import model_manager

    messages = [{"role": "user", "content": "你好，请用一句话介绍自己"}]

    print("\n=== 测试 chat (非流式) ===")
    try:
        result = await model_manager.chat(messages, agent_name="profile")
        print(f"结果: {result[:200] if result else '(空)'}")
        if not result:
            print("[FAIL] empty result!")
        else:
            print("[OK] non-stream works")
    except Exception as e:
        print(f"[FAIL] non-stream error: {e}")


async def test_all_models():
    """测试所有文本模型"""
    from app.core.model_manager import model_manager, TEXT_MODELS

    messages = [{"role": "user", "content": "说一个字：好"}]

    print("\n=== 测试所有文本模型 ===")
    for key, config in TEXT_MODELS.items():
        try:
            result = await model_manager.chat(messages, model_key=key, max_tokens=10)
            status = "OK" if result else "EMPTY"
            print(f"  {key} ({config['name']}): {status} -> {result[:50] if result else ''}")
        except Exception as e:
            print(f"  {key} ({config['name']}): FAIL - {e}")


async def main():
    await test_chat_stream()
    await test_chat()
    await test_all_models()


if __name__ == "__main__":
    asyncio.run(main())
