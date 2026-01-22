#!/usr/bin/env python3
"""
诊断脚本：检查 API Key 权限和模型可用性
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from bailian_client import get_llm_manager, BAILIAN_MODELS

def diagnose():
    print("=" * 70)
    print("百炼 API 诊断工具")
    print("=" * 70)
    
    # 检查环境变量
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ DASHSCOPE_API_KEY 未配置")
        return False
    
    key_preview = f"{api_key[:7]}...{api_key[-4:]}"
    print(f"\n✅ API Key: {key_preview}")
    print(f"   完整长度: {len(api_key)} 字符")
    
    # 初始化客户端
    manager = get_llm_manager()
    if not manager.bailian_client:
        print("❌ 百炼客户端初始化失败")
        return False
    
    print(f"\n当前配置了 {len(BAILIAN_MODELS)} 个模型:")
    for i, model in enumerate(BAILIAN_MODELS, 1):
        print(f"  {i}. {model}")
    
    # 测试模型
    print(f"\n开始测试模型可用性...\n")
    
    test_message = [{"role": "user", "content": "你好"}]
    success_count = 0
    
    for i, model in enumerate(BAILIAN_MODELS, 1):
        print(f"[{i}/{len(BAILIAN_MODELS)}] 测试: {model}")
        try:
            response = manager.bailian_client.chat.completions.create(
                model=model,
                messages=test_message,
                max_tokens=10
            )
            content = response.choices[0].message.content
            print(f"     ✅ 可用 - 响应: {content[:20]}")
            success_count += 1
            break  # 找到一个可用的就够了
            
        except Exception as e:
            error_str = str(e)
            
            if "403" in error_str:
                print(f"     ❌ 403 权限错误 - 免费账户不可访问")
            elif "404" in error_str or "not found" in error_str.lower():
                print(f"     ❌ 404 模型不存在")
            elif "429" in error_str:
                print(f"     ⚠️  429 限流 - 请求过快")
            else:
                print(f"     ❌ 其他错误: {error_str[:80]}")
    
    print("\n" + "=" * 70)
    print(f"诊断完成: {success_count}/{len(BAILIAN_MODELS)} 个模型可用")
    
    if success_count == 0:
        print("\n⚠️  警告: 所有模型都不可用！")
        print("可能原因:")
        print("  1. API Key 是免费账户，权限受限")
        print("  2. 配额已用尽")
        print("  3. API Key 已过期或被禁用")
        print("\n建议:")
        print("  1. 访问 https://bailian.console.aliyun.com/ 检查账户状态")
        print("  2. 确认模型权限和配额")
        print("  3. 尝试使用更基础的模型（如 qwen-turbo）")
    
    return success_count > 0

if __name__ == "__main__":
    success = diagnose()
    sys.exit(0 if success else 1)
