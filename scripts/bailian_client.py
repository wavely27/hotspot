#!/usr/bin/env python3
"""
百炼平台 LLM 客户端配置模块

提供动态模型切换机制，当某个模型额度用完时自动切换到下一个可用模型。
支持百炼作为主供应商，MegaLLM 作为备选。
"""

import os
import time
from typing import Any, Literal
from openai import OpenAI


# ============================================================================
# 百炼模型配置
# ============================================================================

# 百炼模型列表（按优先级排序）
BAILIAN_MODELS = [
    "qwen-long-latest",
    "qwen-long-2025-01-25",
    "qwen-coder-plus",
    "qwen-coder-plus-1106", 
    "qwen-coder-plus-latest",
    "qwen-plus",
    "qwen-turbo",
    "qwen-max",
]

# MegaLLM 备选模型列表
MEGALLM_MODELS = [
    "deepseek-ai/deepseek-v3.1",
    "deepseek-ai/deepseek-v3.1-terminus",
    "qwen/qwen3-next-80b-a3b-instruct",
]

# 错误代码映射（用于判断是否需要切换模型）
QUOTA_ERROR_CODES = {
    "quota_exceeded",
    "insufficient_quota",
    "rate_limit_exceeded",
    "429",
}


# ============================================================================
# LLM 客户端管理
# ============================================================================

class LLMClientManager:
    """管理多个 LLM 客户端（百炼 + MegaLLM）"""
    
    def __init__(self):
        """初始化客户端管理器"""
        self.bailian_client = self._init_bailian_client()
        self.megallm_client = self._init_megallm_client()
        
        # 当前使用的供应商类型
        self.current_provider: Literal["bailian", "megallm"] = "bailian"
        
        # 模型失败计数器（用于跟踪哪些模型已不可用）
        self.failed_models: set[str] = set()
    
    def _init_bailian_client(self) -> OpenAI | None:
        """初始化百炼客户端"""
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            print("[WARN] DASHSCOPE_API_KEY not found, Bailian will be disabled")
            return None
        
        return OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=api_key,
        )
    
    def _init_megallm_client(self) -> OpenAI | None:
        """初始化 MegaLLM 备选客户端"""
        api_key = os.environ.get("MEGALLM_API_KEY")
        if not api_key:
            print("[WARN] MEGALLM_API_KEY not found, MegaLLM fallback will be disabled")
            return None
        
        return OpenAI(
            base_url="https://ai.megallm.io/v1",
            api_key=api_key,
        )
    
    def get_available_models(self) -> list[str]:
        """获取当前可用的模型列表（排除已失败的模型）"""
        if self.current_provider == "bailian":
            models = [m for m in BAILIAN_MODELS if m not in self.failed_models]
            if models:
                return models
            
            # 百炼所有模型都失败了，切换到 MegaLLM
            print("[FALLBACK] All Bailian models exhausted, switching to MegaLLM")
            self.current_provider = "megallm"
        
        # 使用 MegaLLM 模型
        return [m for m in MEGALLM_MODELS if m not in self.failed_models]
    
    def get_current_client(self) -> OpenAI:
        """获取当前应该使用的客户端"""
        if self.current_provider == "bailian" and self.bailian_client:
            return self.bailian_client
        
        if self.megallm_client:
            return self.megallm_client
        
        raise RuntimeError("No available LLM client configured")
    
    def mark_model_failed(self, model: str) -> None:
        """标记某个模型为失败（额度用尽或不可用）"""
        self.failed_models.add(model)
        print(f"[MODEL_FAILED] Marked {model} as unavailable")
    
    def is_quota_error(self, error: Exception) -> bool:
        """判断错误是否为额度/限流相关"""
        error_msg = str(error).lower()
        return any(code in error_msg for code in QUOTA_ERROR_CODES)
    
    def call_with_retry(
        self,
        messages: list[dict],
        response_format: dict | None = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> str | None:
        """
        调用 LLM API，支持自动模型切换和重试
        
        Args:
            messages: 消息列表
            response_format: 响应格式（用于 JSON mode）
            max_retries: 每个模型的最大重试次数
            retry_delay: 重试延迟（秒）
        
        Returns:
            LLM 响应内容，失败返回 None
        """
        available_models = self.get_available_models()
        
        if not available_models:
            print("[ERROR] No available models left")
            return None
        
        for model in available_models:
            print(f"[LLM] Trying model: {model} (provider: {self.current_provider})")
            
            for attempt in range(max_retries):
                try:
                    client = self.get_current_client()
                    
                    kwargs: dict[str, Any] = {
                        "model": model,
                        "messages": messages,
                    }
                    if response_format:
                        kwargs["response_format"] = response_format
                    
                    response = client.chat.completions.create(**kwargs)
                    content = (response.choices[0].message.content or "").strip()
                    
                    if content:
                        print(f"[LLM] ✓ Success with {model}")
                        return content
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # 检查是否为额度/限流错误
                    if self.is_quota_error(e):
                        print(f"[LLM] Quota/Rate limit error with {model}: {e}")
                        self.mark_model_failed(model)
                        break  # 直接切换到下一个模型
                    
                    # 检查是否为模型不可用错误
                    if "unavailable" in error_msg or "not found" in error_msg:
                        print(f"[LLM] Model unavailable: {model}")
                        self.mark_model_failed(model)
                        break
                    
                    # 其他错误（超时、网络等），进行重试
                    if attempt < max_retries - 1:
                        delay = retry_delay * (2 ** attempt)
                        print(f"[LLM] Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"[LLM] Model {model} failed after {max_retries} attempts")
                        # 不标记为失败，可能是临时网络问题
        
        print("[ERROR] All available models failed")
        return None


# ============================================================================
# 全局实例
# ============================================================================

# 创建全局客户端管理器实例
_manager: LLMClientManager | None = None


def get_llm_manager() -> LLMClientManager:
    """获取全局 LLM 客户端管理器实例"""
    global _manager
    if _manager is None:
        _manager = LLMClientManager()
    return _manager


def call_llm(
    messages: list[dict],
    response_format: dict | None = None,
) -> str | None:
    """
    便捷函数：调用 LLM API
    
    Args:
        messages: 消息列表
        response_format: 响应格式（用于 JSON mode）
    
    Returns:
        LLM 响应内容，失败返回 None
    """
    manager = get_llm_manager()
    return manager.call_with_retry(messages, response_format)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    """测试百炼客户端"""
    from dotenv import load_dotenv
    from pathlib import Path
    
    load_dotenv(Path(__file__).parent.parent / ".env")
    
    print("Testing Bailian LLM Client...\n")
    
    manager = get_llm_manager()
    
    # 测试基础对话
    test_messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]
    
    response = manager.call_with_retry(test_messages)
    
    if response:
        print(f"\n✅ Test Success!")
        print(f"Response: {response}")
    else:
        print("\n❌ Test Failed!")
