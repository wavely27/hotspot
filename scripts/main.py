#!/usr/bin/env python3
"""
Daily AI Hotspot Fetcher

从多个 RSS 源抓取内容，通过 Gemini 筛选 AI 相关热点，
存入 Supabase 数据库，并生成每日报告。
"""

import re
import sys
import json
import os
import concurrent.futures
import time
import difflib
import uuid
from typing import Any, cast
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import feedparser
from openai import OpenAI
from supabase import create_client, Client

from fetchers import (
    fetch_rss_feed,
    fetch_aibase_news,
    fetch_aibot_daily_news,
    fetch_ithome_ai_news,
    fetch_github_trending_ai,
    fetch_huggingface_trending,
)

# ============================================================================
# 配置
# ============================================================================

# 每个源最多保留的条目数
MAX_ITEMS_PER_SOURCE = int(os.environ.get("MAX_ITEMS_PER_SOURCE", 10))

# 每个源抓取的原始条目数（用于筛选）
FETCH_ITEMS_PER_SOURCE = int(os.environ.get("FETCH_ITEMS_PER_SOURCE", 30))

LLM_MODELS = [
    "deepseek-ai/deepseek-v3.1",
    "deepseek-ai/deepseek-v3.1-terminus",
    "qwen/qwen3-next-80b-a3b-instruct",
]

# ============================================================================
# 初始化
# ============================================================================

def init_llm() -> OpenAI:
    """初始化 OpenAI 客户端 (MegaLLM)"""
    api_key = os.environ.get("MEGALLM_API_KEY")
    if not api_key:
        raise ValueError("MEGALLM_API_KEY environment variable is required")
    
    return OpenAI(
        base_url="https://ai.megallm.io/v1",
        api_key=api_key
    )


def init_supabase() -> Client:
    """初始化 Supabase 客户端"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    
    return create_client(url, key)


def load_feed_config() -> tuple[list[dict], dict]:
    """加载数据源配置，返回 (feeds, trending)"""
    config_path = Path(__file__).parent.parent / "config" / "info_map.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("feeds", []), config.get("trending", {})


# ============================================================================
# 数据抓取（RSS + 爬虫）
# ============================================================================

# 爬虫函数映射
CRAWLER_MAP = {
    "fetch_aibase_news": fetch_aibase_news,
    "fetch_aibot_daily_news": fetch_aibot_daily_news,
    "fetch_ithome_ai_news": fetch_ithome_ai_news,
}


def fetch_all_feeds(feeds: list[dict]) -> dict[str, list[dict]]:
    """
    抓取所有数据源（支持 RSS 和 爬虫）
    
    Returns:
        dict mapping source name to list of items
    """
    all_items = {}
    
    def fetch_with_timeout(name: str, feed_type: str, feed_config: dict) -> list[dict]:
        """Fetch a single feed with timeout handling"""
        print(f"Fetching: {name} ({feed_type})...")
        items = []
        try:
            if feed_type == "rss":
                url = feed_config.get("url", "")
                if url:
                    # Feedparser handles timeouts internally or we can wrap it
                    items = fetch_rss_feed(url, limit=FETCH_ITEMS_PER_SOURCE)
            elif feed_type == "crawler":
                fetcher_name = feed_config.get("fetcher", "")
                fetcher_func = CRAWLER_MAP.get(fetcher_name)
                if fetcher_func:
                    items = fetcher_func(limit=FETCH_ITEMS_PER_SOURCE)
                else:
                    print(f"  [WARN] Unknown fetcher: {fetcher_name}")
        except Exception as e:
            print(f"  [ERROR] Failed to fetch {name}: {e}")
            
        if items:
            print(f"  Found {len(items)} items from {name}")
            return items
        print(f"  No items found from {name}")
        return []

    # Use ThreadPoolExecutor for parallel fetching
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_feed = {}
        for feed in feeds:
            name = feed["name"]
            feed_type = feed.get("type", "rss")
            future = executor.submit(fetch_with_timeout, name, feed_type, feed)
            future_to_feed[future] = name

        for future in concurrent.futures.as_completed(future_to_feed):
            name = future_to_feed[future]
            try:
                items = future.result()
                if items:
                    all_items[name] = items
            except Exception as e:
                print(f"  [ERROR] Exception fetching {name}: {e}")

    return all_items


# ============================================================================
# LLM API 调用（带重试机制）
# ============================================================================

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5

def call_llm_with_retry(
    client: OpenAI,
    messages: list[dict],
    response_format: dict | None = None,
) -> str | None:
    for model in LLM_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                
                response = client.chat.completions.create(**kwargs)
                return (response.choices[0].message.content or "").strip()
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = "rate_limit" in error_msg or "429" in error_msg
                is_timeout = "timeout" in error_msg or "timed out" in error_msg
                is_unavailable = "unavailable" in error_msg
                
                if is_unavailable:
                    print(f"  [FALLBACK] {model} unavailable, trying next model...")
                    break
                
                if attempt < MAX_RETRIES - 1 and (is_rate_limit or is_timeout):
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    print(f"  [RETRY] {model} attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"  [FALLBACK] {model} failed after {attempt + 1} attempts, trying next model...")
                    break
    
    print("  [ERROR] All LLM models failed")
    return None


# ============================================================================
# Gemini 筛选
# ============================================================================

FILTER_PROMPT = """你是一个 AI 技术热点筛选助手。请从以下文章列表中，筛选出与 AI/人工智能最相关、最有价值的内容。

评判标准：
1. 与 AI、机器学习、深度学习、大语言模型等直接相关
2. 内容有价值（技术突破、重要发布、行业动态等）
3. 优先选择热度高、影响力大的内容

请从下面的文章中选出最多 {limit} 篇最符合条件的文章。

文章列表：
{articles}

请以 JSON 格式返回结果，**所有文本内容必须翻译成中文**，格式如下：
```json
{{
  "selected": [
    {{
      "index": 0,
      "title_cn": "中文标题",
      "reason_cn": "中文推荐理由（作为该资讯的简短总结，50字以内）",
      "tags": ["trending", "tech"],
      "keywords": ["关键词1", "关键词2"]
    }}
  ]
}}
```

tags 标签说明（可多选）：
- trending: 热点速览 - 适合产品经理/创业者/泛科技爱好者（新产品发布、应用场景、有趣动态）
- tech: 技术前沿 - 适合开发者/技术人员（开源项目、技术教程、API更新、技术突破）
- business: 商业洞察 - 适合投资人/商业决策者（融资、并购、公司战略、市场分析）

keywords: 提取 2-5 个核心关键词（如：GPT-5、OpenAI、多模态、开源）

只返回 JSON，不要其他内容。index 是文章在列表中的索引（从 0 开始）。
"""

SUMMARY_PROMPT = """请根据以下今日 AI 热点新闻的标题和推荐理由，写一段约 50 字的简短日报综述。
综述应点出今天最值得关注的 1-3 个核心热点事件。

热点列表：
{content}

请直接返回综述文本，不要加任何前缀或格式。
"""

GITHUB_TRANSLATE_PROMPT = """请为以下 GitHub AI 项目生成中文介绍。

项目列表：
{projects}

请以 JSON 格式返回结果：
```json
{{
  "translated": [
    {{
      "index": 0,
      "description_cn": "项目中文介绍（一句话，50字以内）",
      "ai_reason": "推荐理由（为什么值得关注，30字以内）"
    }}
  ]
}}
```

只返回 JSON，不要其他内容。
"""

HUGGINGFACE_TRANSLATE_PROMPT = """请为以下 HuggingFace 热门模型生成中文介绍。

模型列表：
{models}

请以 JSON 格式返回结果：
```json
{{
  "translated": [
    {{
      "index": 0,
      "description_cn": "模型中文介绍（一句话，50字以内）",
      "ai_reason": "推荐理由（为什么值得关注，30字以内）"
    }}
  ]
}}
```

只返回 JSON，不要其他内容。
"""


def calculate_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的相似度"""
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def deduplicate_items(items: list[dict], threshold: float = 0.6) -> list[dict]:
    """
    对热点进行去重和聚合
    
    Args:
        items: 热点列表
        threshold: 相似度阈值 (0.0 - 1.0)
    
    Returns:
        处理后的热点列表（包含 duplicate_group 信息）
    """
    if not items:
        return []
    
    # 按来源分组，避免同一来源内部去重（假设同一来源不会发重复内容）
    # 但这里我们要跨来源去重
    
    # 结果列表
    processed_items = []
    
    # 记录已处理的索引
    processed_indices = set()
    
    for i in range(len(items)):
        if i in processed_indices:
            continue
            
        current_item = items[i]
        current_item["duplicate_group"] = str(uuid.uuid4())
        current_item["is_primary"] = True
        current_item["similarity_score"] = 0
        
        # 查找重复项
        duplicates = []
        for j in range(i + 1, len(items)):
            if j in processed_indices:
                continue
                
            compare_item = items[j]
            
            # 比较标题相似度
            title_sim = calculate_similarity(current_item["title"], compare_item["title"])
            
            # 如果标题相似度高，视为重复
            if title_sim >= threshold:
                duplicates.append({
                    "index": j,
                    "score": title_sim,
                    "item": compare_item
                })
        
        # 处理重复项
        for dup in duplicates:
            idx = dup["index"]
            processed_indices.add(idx)
            
            dup_item = dup["item"]
            dup_item["duplicate_group"] = current_item["duplicate_group"]
            dup_item["is_primary"] = False
            dup_item["similarity_score"] = dup["score"]
            dup_item["duplicate_of"] = current_item["url"] # 逻辑上指向主条目，实际存储时需要先存主条目获取ID，或者仅用 group ID 关联
            
            processed_items.append(dup_item)
            
            # 合并标签和关键词
            if "tags" in dup_item:
                current_item["tags"] = list(set(current_item.get("tags", []) + dup_item["tags"]))
            if "keywords" in dup_item:
                current_item["keywords"] = list(set(current_item.get("keywords", []) + dup_item["keywords"]))

        processed_indices.add(i)
        processed_items.append(current_item)
        
    return processed_items

def filter_items_with_gemini(
    client: OpenAI,
    items: list[dict],
    limit: int = MAX_ITEMS_PER_SOURCE
) -> list[dict]:
    """
    使用 LLM 筛选最相关的文章，并生成中文标题和理由
    """
    if not items:
        return []
    
    # 构建文章列表文本
    articles_text = ""
    for i, item in enumerate(items):
        articles_text += f"\n[{i}] 标题: {item['title']}\n"
        if item.get("summary"):
            articles_text += f"    摘要: {item['summary'][:200]}\n"
    
    prompt = FILTER_PROMPT.format(limit=limit, articles=articles_text)
    
    response_text = call_llm_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    if not response_text:
        return items[:limit]
    
    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if not json_match:
        print("  [WARN] Could not parse LLM response, returning original items")
        return items[:limit]
    
    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError:
        print("  [WARN] Invalid JSON from LLM, returning original items")
        return items[:limit]
    
    selected_map = {item["index"]: item for item in result.get("selected", [])}
    selected_indices = [item["index"] for item in result.get("selected", [])]
    
    filtered = []
    for idx in selected_indices:
        if 0 <= idx < len(items):
            item = items[idx].copy()
            gemini_data = selected_map.get(idx, {})
            
            if gemini_data.get("title_cn"):
                item["title"] = gemini_data["title_cn"]
            if gemini_data.get("reason_cn"):
                item["ai_reason"] = gemini_data["reason_cn"]
            if gemini_data.get("tags"):
                item["tags"] = gemini_data["tags"]
            if gemini_data.get("keywords"):
                item["keywords"] = gemini_data["keywords"]
            
            filtered.append(item)
    
    return filtered[:limit]


ANALYSIS_PROMPT = """请根据以下今日 AI 热点新闻，生成一份深度的日报分析。

热点列表：
{content}

请以 JSON 格式返回结果，包含以下字段：
1. focus_events: 挑选 1-3 个最重要的焦点事件，进行深度解读。
2. overview: 今日整体趋势综述（100字左右）。
3. keywords: 提取今日所有资讯的核心关键词及其热度（出现频率/重要性，1-10分）。

JSON 格式如下：
```json
{{
  "focus_events": [
    {{
      "title": "事件标题",
      "summary": "事件简述",
      "why": "发生原因/背景（为什么重要？）",
      "impact": "后续影响/行业意义"
    }}
  ],
  "overview": "今日 AI 领域整体呈现...趋势，其中...",
  "keywords": {{
    "关键词1": 10,
    "关键词2": 8,
    "关键词3": 5
  }}
}}
```

只返回 JSON，不要其他内容。
"""

def generate_daily_analysis(client: OpenAI, all_selected: dict[str, list[dict]]) -> dict | None:
    """生成每日深度分析"""
    content = ""
    for source, items in all_selected.items():
        for item in items:
            title = item.get("title", "")
            reason = item.get("ai_reason", "")
            tags = ",".join(item.get("tags", []))
            content += f"- [{tags}] {title}: {reason}\n"
    
    if not content:
        return None

    prompt = ANALYSIS_PROMPT.format(content=content[:8000]) # 增加上下文长度
    
    response_text = call_llm_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    if not response_text:
        return None
    
    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if not json_match:
        return None
        
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return None

def upsert_daily_analysis(supabase: Client, analysis_data: dict) -> bool:
    """保存每日深度分析"""
    if not analysis_data:
        return False
        
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    data = {
        "report_date": today,
        "focus_events": analysis_data.get("focus_events", []),
        "overview": analysis_data.get("overview", ""),
        "keywords": analysis_data.get("keywords", {})
    }
    
    try:
        supabase.table("daily_analysis").upsert(data, on_conflict="report_date").execute()
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to save daily analysis: {e}")
        return False

def generate_daily_summary(client: OpenAI, all_selected: dict[str, list[dict]]) -> str:
    content = ""
    for source, items in all_selected.items():
        for item in items:
            title = item.get("title", "")
            reason = item.get("ai_reason", "")
            content += f"- {title}: {reason}\n"
    
    if not content:
        return "今日暂无重点资讯。"

    prompt = SUMMARY_PROMPT.format(content=content[:5000])
    
    response_text = call_llm_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response_text or "今日 AI 热点资讯汇总。"


def translate_github_trending(client: OpenAI, items: list[dict], limit: int = 20) -> list[dict]:
    if not items:
        return []
    
    items = items[:limit]
    projects_text = ""
    for i, item in enumerate(items):
        projects_text += f"\n[{i}] {item['name']}"
        projects_text += f"\n    ⭐{item['stars']} | Language: {item.get('language', 'N/A')}"
        if item.get("description"):
            projects_text += f"\n    {item['description'][:200]}"
    
    prompt = GITHUB_TRANSLATE_PROMPT.format(projects=projects_text)
    
    response_text = call_llm_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    if not response_text:
        return items
    
    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if not json_match:
        return items
    
    try:
        result = json.loads(json_match.group())
        translated_map = {t["index"]: t for t in result.get("translated", [])}
        
        for i, item in enumerate(items):
            if i in translated_map:
                t = translated_map[i]
                item["description_cn"] = t.get("description_cn", "")
                item["ai_reason"] = t.get("ai_reason", "")
        
        return items
    except (json.JSONDecodeError, KeyError):
        return items


def translate_huggingface_trending(client: OpenAI, items: list[dict], limit: int = 20) -> list[dict]:
    if not items:
        return []
    
    items = items[:limit]
    models_text = ""
    for i, item in enumerate(items):
        models_text += f"\n[{i}] {item['model_id']}"
        models_text += f"\n    🔥{item.get('trending_score', 0)} | Task: {item.get('pipeline_tag', 'N/A')}"
        models_text += f"\n    Downloads: {item.get('downloads', 0)} | Likes: {item.get('likes', 0)}"
    
    prompt = HUGGINGFACE_TRANSLATE_PROMPT.format(models=models_text)
    
    response_text = call_llm_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    if not response_text:
        return items
    
    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if not json_match:
        return items
    
    try:
        result = json.loads(json_match.group())
        translated_map = {t["index"]: t for t in result.get("translated", [])}
        
        for i, item in enumerate(items):
            if i in translated_map:
                t = translated_map[i]
                item["description_cn"] = t.get("description_cn", "")
                item["ai_reason"] = t.get("ai_reason", "")
        
        return items
    except (json.JSONDecodeError, KeyError):
        return items


# ============================================================================
# 数据库操作
# ============================================================================

def ensure_tables_exist(supabase: Client) -> None:
    """确保所需的表存在，如果不存在则跳过日报保存"""
    try:
        # 检查 daily_reports 表是否存在
        supabase.table("daily_reports").select("id").limit(1).execute()
        # print("  daily_reports table: OK")
    except Exception:
        print("  [WARN] daily_reports table not found. Daily report will not be saved.")
        print("  To create it, run this SQL in Supabase Dashboard:")
        print("  CREATE TABLE daily_reports (")
        print("    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,")
        print("    report_date DATE DEFAULT CURRENT_DATE UNIQUE,")
        print("    content TEXT NOT NULL,")
        print("    summary TEXT,")
        print("    created_at TIMESTAMPTZ DEFAULT NOW()")
        print("  );")


def upsert_hotspots(supabase: Client, items: list[dict], source: str) -> int:
    """
    将热点数据写入 Supabase
    """
    if not items:
        return 0
    
    records = []
    for item in items:
        records.append({
            "title": item["title"],
            "url": item["url"],
            "summary": item.get("ai_reason") or item.get("summary", ""), # 优先使用 AI 生成的中文理由
            "source": source,
            "tags": item.get("tags", []),
            "keywords": item.get("keywords", []),
            "duplicate_group": item.get("duplicate_group"),
            "is_primary": item.get("is_primary", True),
            "similarity_score": item.get("similarity_score", 0),
            "is_published": True,
        })
    
    try:
        # 使用 upsert，以 url 为冲突检测字段
        result = supabase.table("hotspots").upsert(
            records,
            on_conflict="url"
        ).execute()
        
        return len(result.data) if result.data else 0
    
    except Exception as e:
        print(f"  [ERROR] Failed to upsert hotspots: {e}")
        return 0


def save_daily_report(supabase: Client, report_content: str, summary: str = "") -> bool:
    """保存每日报告到数据库（增量模式：追加新来源，不覆盖已有内容）"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    try:
        existing = supabase.table("daily_reports").select("content, summary").eq("report_date", today).execute()
        
        # Cast data to a list of dicts to satisfy type checker
        existing_data = cast(list[dict[str, Any]], existing.data)

        if existing_data:
            old_content = str(existing_data[0].get("content", "") or "")
            old_summary = str(existing_data[0].get("summary", "") or "")
            
            existing_sources = set(re.findall(r"^## (.+)$", old_content, re.MULTILINE))
            new_sections = re.split(r"(?=^## )", report_content, flags=re.MULTILINE)
            
            new_content_parts = []
            for section in new_sections:
                match = re.match(r"^## (.+)$", section, re.MULTILINE)
                if match:
                    source_name = match.group(1)
                    if source_name not in existing_sources:
                        new_content_parts.append(section.strip())
            
            if new_content_parts:
                merged_content = old_content.rstrip() + "\n\n" + "\n\n".join(new_content_parts)
            else:
                merged_content = old_content
            
            merged_summary = summary if summary else old_summary
            
            data = {
                "report_date": today,
                "content": merged_content,
                "summary": merged_summary
            }
        else:
            data = {
                "report_date": today,
                "content": report_content,
                "summary": summary
            }
        
        supabase.table("daily_reports").upsert(data, on_conflict="report_date").execute()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save daily report: {e}")
        return False


def upsert_github_trending(supabase: Client, items: list[dict]) -> int:
    if not items:
        return 0
    
    records = []
    for item in items:
        records.append({
            "name": item["name"],
            "url": item["url"],
            "description": item.get("description", ""),
            "description_cn": item.get("description_cn", ""),
            "stars": item.get("stars", 0),
            "forks": item.get("forks", 0),
            "language": item.get("language", ""),
            "topics": item.get("topics", []),
            "ai_reason": item.get("ai_reason", ""),
            "is_published": True,
        })
    
    try:
        result = supabase.table("github_trending").upsert(
            records, on_conflict="url"
        ).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        print(f"  [ERROR] Failed to upsert github_trending: {e}")
        return 0


def upsert_huggingface_trending(supabase: Client, items: list[dict]) -> int:
    if not items:
        return 0
    
    records = []
    for item in items:
        records.append({
            "model_id": item["model_id"],
            "url": item["url"],
            "description_cn": item.get("description_cn", ""),
            "likes": item.get("likes", 0),
            "downloads": item.get("downloads", 0),
            "trending_score": item.get("trending_score", 0),
            "pipeline_tag": item.get("pipeline_tag", ""),
            "tags": item.get("tags", []),
            "ai_reason": item.get("ai_reason", ""),
            "is_published": True,
        })
    
    try:
        result = supabase.table("huggingface_trending").upsert(
            records, on_conflict="url"
        ).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        print(f"  [ERROR] Failed to upsert huggingface_trending: {e}")
        return 0


# ============================================================================
# 报告生成
# ============================================================================

def generate_daily_report(
    all_selected: dict[str, list[dict]], 
    daily_summary: str = ""
) -> str:
    """生成每日 Markdown 报告（中文版）"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    lines = [
        f"# AI 热点日报 - {today}",
        "",
        f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
    ]
    
    if daily_summary:
        lines.append(f"> **今日综述**：{daily_summary}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    total_count = sum(len(items) for items in all_selected.values())
    lines.append(f"今日共收录 **{total_count}** 条热点，来自 **{len(all_selected)}** 个信息源。")
    lines.append("")
    
    for source, items in all_selected.items():
        lines.append(f"## {source}")
        lines.append("")
        
        for i, item in enumerate(items):
            title = item["title"] # 已经是中文
            url = item["url"]
            # 优先使用 AI 生成的理由，否则使用原文摘要
            reason = item.get("ai_reason") or item.get("summary", "")
            # 限制摘要长度，避免过长
            if reason and len(reason) > 200:
                reason = reason[:200] + "..."
            
            lines.append(f"### {i+1}. [{title}]({url})")
            if reason:
                lines.append(f"> {reason}")
            lines.append("")
        
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# 主函数
# ============================================================================

def main():
    print("=" * 60)
    print("AI Hotspot Daily Fetcher")
    print("=" * 60)
    print()
    
    print("[1/8] Initializing...")
    try:
        client = init_llm()
        supabase = init_supabase()
        feeds, trending_config = load_feed_config()
        
        # Allow limiting feeds for testing
        max_feeds = os.environ.get("MAX_FEEDS")
        if max_feeds:
            print(f"[TEST] Limiting to first {max_feeds} feeds")
            feeds = feeds[:int(max_feeds)]
            # Clear trending if testing speed
            trending_config = {}

        print(f"  Loaded {len(feeds)} feed sources + {len(trending_config)} trending sources")
        ensure_tables_exist(supabase)
    except Exception as e:
        print(f"[FATAL] Initialization failed: {e}")
        sys.exit(1)
    
    print()
    print("[2/8] Fetching feeds (RSS + crawlers)...")
    raw_data = fetch_all_feeds(feeds)
    
    if not raw_data:
        print("[WARN] No data fetched from any source")
    
    print()
    print("[3/8] Filtering & Translating feeds with LLM (Parallel)...")
    all_selected = {}

    def process_source_with_llm(source_name: str, source_items: list[dict]) -> tuple[str, list[dict]]:
        """Process a single source with LLM"""
        print(f"  Processing: {source_name} ({len(source_items)} items)")
        try:
            # Re-initialize client for thread safety if needed, or pass it in
            # OpenAI client is thread-safe, but we can also instantiate a new one if we see issues
            local_client = init_llm() 
            selected_items = filter_items_with_gemini(local_client, source_items)
            return source_name, selected_items
        except Exception as e:
            print(f"  [ERROR] Failed to process {source_name}: {e}")
            return source_name, []

    # Use ThreadPoolExecutor for parallel LLM processing
    # Limit workers to avoid Rate Limit errors (429) from API
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_source = {
            executor.submit(process_source_with_llm, source, items): source 
            for source, items in raw_data.items()
        }
        
        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                name, selected = future.result()
                if selected:
                    all_selected[name] = selected
                    print(f"    Selected {len(selected)} items for {name}")
            except Exception as e:
                print(f"    [ERROR] Exception processing {source}: {e}")

    print()
    print("[3.5/8] Deduplicating items across sources...")
    # Flatten items for deduplication
    flat_items = []
    for source, items in all_selected.items():
        for item in items:
            item["_source_key"] = source
            flat_items.append(item)
            
    if flat_items:
        deduped_items = deduplicate_items(flat_items)
        print(f"  Processed {len(flat_items)} items, found {len([i for i in deduped_items if not i.get('is_primary')])} duplicates")
        
        # Re-group by source
        all_selected = {}
        for item in deduped_items:
            source = item.pop("_source_key")
            if source not in all_selected:
                all_selected[source] = []
            all_selected[source].append(item)
    
    print()
    print("[4/8] Fetching trending data...")
    github_items = []
    huggingface_items = []
    
    if "github" in trending_config:
        print("  Fetching GitHub Trending AI...")
        github_items = fetch_github_trending_ai(limit=30)
        print(f"    Found {len(github_items)} repos")
    
    if "huggingface" in trending_config:
        print("  Fetching HuggingFace Trending...")
        huggingface_items = fetch_huggingface_trending(limit=30)
        print(f"    Found {len(huggingface_items)} models")
    
    print()
    print("[5/8] Translating trending data with LLM...")
    if github_items:
        print("  Translating GitHub items...")
        github_items = translate_github_trending(client, github_items, limit=20)
    if huggingface_items:
        print("  Translating HuggingFace items...")
        huggingface_items = translate_huggingface_trending(client, huggingface_items, limit=20)
    
    print()
    print("[6/8] Generating daily summary & analysis...")
    daily_summary = ""
    daily_analysis = None
    
    if all_selected:
        try:
            # 并行生成综述和深度分析
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_summary = executor.submit(generate_daily_summary, client, all_selected)
                future_analysis = executor.submit(generate_daily_analysis, client, all_selected)
                
                daily_summary = future_summary.result()
                print(f"  Summary: {daily_summary}")
                
                daily_analysis = future_analysis.result()
                if daily_analysis:
                    print(f"  Analysis generated: {len(daily_analysis.get('focus_events', []))} focus events")
        except Exception as e:
            print(f"  [WARN] Skipped summary/analysis generation: {e}")
    
    print()
    print("[7/8] Saving to database...")
    total_saved = 0
    
    for source, items in all_selected.items():
        count = upsert_hotspots(supabase, items, source)
        total_saved += count
        print(f"  {source}: {count} records")
    
    if daily_analysis:
        if upsert_daily_analysis(supabase, daily_analysis):
            print("  Daily analysis saved successfully")
    
    if github_items:
        count = upsert_github_trending(supabase, github_items)
        total_saved += count
        print(f"  GitHub Trending: {count} records")
    
    if huggingface_items:
        count = upsert_huggingface_trending(supabase, huggingface_items)
        total_saved += count
        print(f"  HuggingFace Trending: {count} records")
    
    print(f"  Total saved: {total_saved} records")
    
    print()
    print("[8/8] Generating & Saving daily report...")
    report = generate_daily_report(all_selected, daily_summary)
    
    if save_daily_report(supabase, report, daily_summary):
        print("  Daily report saved successfully")
    else:
        print("  [WARN] Failed to save daily report")
    
    print()
    print("=" * 60)
    print("REPORT PREVIEW")
    print("=" * 60)
    print(report[:2000])
    if len(report) > 2000:
        print("... (truncated)")
    
    print()
    print("=" * 60)
    print("COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
