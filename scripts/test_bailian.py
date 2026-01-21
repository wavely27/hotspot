#!/usr/bin/env python3
"""
百炼 API 连接和模型可用性测试脚本
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from bailian_client import get_llm_manager

def test_bailian_connection():
    """测试百炼 API 连接"""
    print("=" * 60)
    print("百炼 API 连接测试")
    print("=" * 60)
    
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    megallm_key = os.environ.get("MEGALLM_API_KEY")
    
    print(f"\n✓ DASHSCOPE_API_KEY: {api_key[:20]}..." if api_key else "✗ DASHSCOPE_API_KEY not found")
    print(f"✓ MEGALLM_API_KEY: {megallm_key[:20]}..." if megallm_key else "✗ MEGALLM_API_KEY not found")
    
    print("\n初始化 LLM 客户端管理器...")
    manager = get_llm_manager()
    
    print(f"当前供应商: {manager.current_provider}")
    print(f"可用模型数量: {len(manager.get_available_models())}")
    print(f"百炼客户端状态: {'✓ 已配置' if manager.bailian_client else '✗ 未配置'}")
    print(f"MegaLLM 客户端状态: {'✓ 已配置' if manager.megallm_client else '✗ 未配置'}")
    
    print("\n" + "=" * 60)
    print("测试 1: 基础对话")
    print("=" * 60)
    
    test_messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]
    
    response = manager.call_with_retry(test_messages)
    
    if response:
        print(f"\n✅ 测试成功!")
        print(f"使用的供应商: {manager.current_provider}")
        print(f"响应内容: {response[:200]}...")
    else:
        print("\n❌ 测试失败!")
        return False
    
    print("\n" + "=" * 60)
    print("测试 2: JSON 模式")
    print("=" * 60)
    
    json_messages = [
        {
            "role": "user",
            "content": """请以 JSON 格式返回以下信息：
{
  "name": "你的名字",
  "version": "你的版本",
  "capabilities": ["能力1", "能力2", "能力3"]
}"""
        }
    ]
    
    response = manager.call_with_retry(
        json_messages,
        response_format={"type": "json_object"}
    )
    
    if response:
        print(f"\n✅ JSON 模式测试成功!")
        print(f"响应内容: {response[:300]}...")
    else:
        print("\n❌ JSON 模式测试失败!")
        return False
    
    print("\n" + "=" * 60)
    print("测试 3: 查看模型状态")
    print("=" * 60)
    
    print(f"\n当前供应商: {manager.current_provider}")
    print(f"已失败的模型: {manager.failed_models if manager.failed_models else '无'}")
    print(f"剩余可用模型: {manager.get_available_models()[:3]}...")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    import sys
    success = test_bailian_connection()
    sys.exit(0 if success else 1)
