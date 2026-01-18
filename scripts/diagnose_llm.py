import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

api_key = os.environ.get("MEGALLM_API_KEY")
base_url = "https://ai.megallm.io/v1"

print(f"Checking MegaLLM connection...")
print(f"Base URL: {base_url}")
print(f"API Key: {api_key[:8]}... (len={len(api_key)})")

client = OpenAI(api_key=api_key, base_url=base_url)

# 1. 列出可用模型
print("\n[1/2] Listing available models...")
try:
    models_response = client.models.list()
    # 打印前 50 个模型
    print(f"Found {len(models_response.data)} models.")
    for i, model in enumerate(models_response.data[:50]):
        print(f"  - {model.id}")
    
    # 尝试找到 GPT/Kimi/DeepSeek 相关模型
    keyword_models = [m.id for m in models_response.data if any(k in m.id.lower() for k in ['gpt', 'moonshot', 'deepseek', 'kimi'])]
    print(f"\nTarget models found: {keyword_models}")

except Exception as e:
    print(f"❌ Failed to list models: {e}")
    # 如果列出失败，尝试硬编码测试
    models_response = None

# 2. 测试生成
test_model = "gpt-4o"
if models_response and models_response.data:
    # 优先尝试 gpt-4o，如果没有则用列表中的第一个
    available_ids = [m.id for m in models_response.data]
    if "gpt-4o" in available_ids:
        test_model = "gpt-4o"
    elif "gpt-3.5-turbo" in available_ids:
        test_model = "gpt-3.5-turbo"
    else:
        test_model = available_ids[0]

print(f"\n[2/2] Testing generation with model: '{test_model}'...")
try:
    response = client.chat.completions.create(
        model=test_model,
        messages=[{"role": "user", "content": "Hi, are you working?"}],
        max_tokens=10
    )
    print(f"✅ Success! Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ Generation failed: {e}")
