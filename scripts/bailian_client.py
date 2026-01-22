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
# 优先级策略：本地验证可用的模型 > 常用模型 > 其他备选模型
BAILIAN_MODELS = [
    # 第一优先级：本地验证 100% 可用的模型
    "qwen-turbo",
    "qwen-turbo-latest",
    "qwen2.5-7b-instruct",
    "qwen2.5-14b-instruct",
    "qwen-plus",
    
    # 第二优先级：常用高性能模型
    "qwen-plus-latest",
    "qwen-max-latest",
    "qwen-max",
    "qwen3-max",
    "qwen-long-latest",
    
    # 第三优先级：其他备选模型
    "qwen-long-2025-01-25",
    "qwen-long",
    "qwen-coder-plus",
    "qwen-coder-plus-latest",
    "qwen-coder-plus-1106",
    "qwen-coder-turbo-latest",
    "qwen-coder-turbo-0919",
    "qwen-coder-turbo",
    "qwen-max-2025-01-25",
    "qwen-max-0919",
    "qwen3-max-preview",
    "qwen3-max-2025-09-23",
    "qwen-max-0428",
    "qwen-max-0403",
    "qwen-plus-character",
    "qwen-plus-2025-12-01",
    "qwen-plus-2025-09-11",
    "qwen-plus-2025-07-28",
    "qwen-plus-2025-07-14",
    "qwen-plus-2025-04-28",
    "qwen-plus-2025-01-25",
    "qwen-plus-1220",
    "qwen-plus-1127",
    "qwen-plus-1125",
    "qwen-plus-0919",
    "qwen-plus-0806",
    "qwen-plus-0723",
    "qwen-plus-0112",
    "qwen-turbo-2025-07-15",
    "qwen-turbo-2025-04-28",
    "qwen-turbo-2025-02-11",
    "qwen-turbo-1101",
    "qwen-turbo-0919",
    "qwen-turbo-0624",
    "qwen-math-plus-latest",
    "qwen-math-plus",
    "qwen-math-plus-0919",
    "qwen-math-plus-0816",
    "qwen-math-turbo-latest",
    "qwen-math-turbo-0919",
    "qwen-math-turbo",
    "qwen1.5-110b-chat",
    "qwen1.5-72b-chat",
    "qwen1.5-32b-chat",
    "qwen1.5-14b-chat",
    "qwen1.5-7b-chat",
    "qwen2-72b-instruct",
    "qwen2-57b-a14b-instruct",
    "qwen2-7b-instruct",
    "qwen2.5-72b-instruct",
    "qwen2.5-32b-instruct",
    "qwen2.5-14b-instruct-1m",
    "qwen2.5-7b-instruct-1m",
    "qwen2.5-3b-instruct",
    "qwen2.5-1.5b-instruct",
    "qwen2.5-0.5b-instruct",
    "qwen2.5-math-72b-instruct",
    "qwen2.5-math-7b-instruct",
    "qwen2.5-coder-32b-instruct",
    "qwen2.5-coder-14b-instruct",
    "qwen2.5-coder-7b-instruct",
    "qwen-vl-max-latest",
    "qwen-vl-max",
    "qwen-vl-max-2025-08-13",
    "qwen-vl-max-2025-04-08",
    "qwen-vl-max-2025-04-02",
    "qwen-vl-max-2025-01-25",
    "qwen-vl-max-1230",
    "qwen-vl-max-1119",
    "qwen-vl-max-1030",
    "qwen-vl-max-0809",
    "qwen-vl-plus-latest",
    "qwen-vl-plus",
    "qwen-vl-plus-2025-08-15",
    "qwen-vl-plus-2025-05-07",
    "qwen-vl-plus-2025-01-25",
    "qwen-vl-plus-0809",
    "qwen-vl-plus-0102",
    "qwen-vl-ocr-latest",
    "qwen-vl-ocr",
    "qwen-vl-ocr-2025-11-20",
    "qwen-vl-ocr-2025-08-28",
    "qwen-vl-ocr-2025-04-13",
    "qwen-vl-ocr-1028",
    "qwen2-vl-72b-instruct",
    "qwen2-vl-7b-instruct",
    "qwen2-vl-2b-instruct",
    "qwen2.5-vl-32b-instruct",
    "qwen2.5-vl-7b-instruct",
    "qwen2.5-vl-3b-instruct",
    "qvq-max-latest",
    "qvq-max",
    "qvq-max-2025-05-15",
    "qvq-max-2025-03-25",
    "qvq-72b-preview",
    "qvq-plus-latest",
    "qvq-plus",
    "qvq-plus-2025-05-15",
    "qwq-plus-latest",
    "qwq-plus",
    "qwq-plus-2025-03-05",
    "qwq-32b-preview",
    "qwq-32b",
    "qwen3-235b-a22b-instruct-2507",
    "qwen3-235b-a22b-thinking-2507",
    "qwen3-235b-a22b",
    "qwen3-next-80b-a3b-instruct",
    "qwen3-next-80b-a3b-thinking",
    "qwen3-32b",
    "qwen3-30b-a3b-instruct-2507",
    "qwen3-30b-a3b-thinking-2507",
    "qwen3-30b-a3b",
    "qwen3-14b",
    "qwen3-8b",
    "qwen3-4b",
    "qwen3-1.7b",
    "qwen3-0.6b",
    "qwen3-coder-480b-a35b-instruct",
    "qwen3-coder-plus",
    "qwen3-coder-plus-2025-09-23",
    "qwen3-coder-plus-2025-07-22",
    "qwen3-coder-flash",
    "qwen3-coder-flash-2025-07-28",
    "qwen3-coder-30b-a3b-instruct",
    "qwen3-vl-235b-a22b-thinking",
    "qwen3-vl-235b-a22b-instruct",
    "qwen3-vl-plus",
    "qwen3-vl-plus-2025-12-19",
    "qwen3-vl-plus-2025-09-23",
    "qwen3-vl-30b-a3b-thinking",
    "qwen3-vl-30b-a3b-instruct",
    "qwen3-vl-flash",
    "qwen3-vl-flash-2025-10-15",
    "qwen3-vl-8b-thinking",
    "qwen3-vl-8b-instruct",
    "qwen-flash",
    "qwen-flash-2025-07-28",
    "gui-plus",
    "qwen-mt-plus",
    "qwen-mt-turbo",
    "qwen-mt-flash",
    "qwen-mt-lite",
    "tongyi-intent-detect-v3",
    "opennlu-v1",
    "deepseek-v3.2-exp",
    "deepseek-v3.2",
    "deepseek-v3.1",
    "deepseek-v3",
    "deepseek-r1",
    "deepseek-r1-0528",
    "deepseek-r1-distill-qwen-32b",
    "deepseek-r1-distill-qwen-14b",
    "deepseek-r1-distill-qwen-7b",
    "deepseek-r1-distill-llama-70b",
    "wan2.2-kf2v-flash",
    "glm-4.7",
    "glm-4.6",
    "glm-4.5",
    "glm-4.5-air",
    "llama-4-maverick-17b-128e-instruct",
    "llama-4-scout-17b-16e-instruct",
    "Moonshot-Kimi-K2-Instruct",
    "kimi-k2-thinking",
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
        
        # 打印 Key 的前后4位用于诊断（安全起见不打印完整 Key）
        key_prefix = api_key[:7] if len(api_key) > 10 else "***"
        key_suffix = api_key[-4:] if len(api_key) > 10 else "***"
        print(f"[INFO] Using Bailian API Key: {key_prefix}...{key_suffix}")
        
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
        max_retries: int = 2,
        retry_delay: int = 3,
    ) -> str | None:
        """
        调用 LLM API，支持自动模型切换和重试
        
        Args:
            messages: 消息列表
            response_format: 响应格式（用于 JSON mode）
            max_retries: 每个模型的最大重试次数（默认 2，优化以减少总耗时）
            retry_delay: 重试延迟基数（默认 3 秒，使用指数退避）
        
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
                    
                    # 检查是否为权限错误（免费账户访问付费模型）
                    if "403" in str(e) or "permission" in error_msg or "insufficient_permissions" in error_msg:
                        print(f"[LLM] Permission denied (free tier limitation): {model}")
                        self.mark_model_failed(model)
                        break
                    
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
