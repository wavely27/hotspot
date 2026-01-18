#!/usr/bin/env python3
"""
Daily AI Hotspot Fetcher

从多个 RSS 源抓取内容，通过 Gemini 筛选 AI 相关热点，
存入 Supabase 数据库，并生成每日报告。
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import google.generativeai as genai
from supabase import create_client, Client

# ============================================================================
# 配置
# ============================================================================

# 每个源最多保留的条目数
MAX_ITEMS_PER_SOURCE = 10

# 每个源抓取的原始条目数（用于筛选）
FETCH_ITEMS_PER_SOURCE = 30

# Gemini 模型
GEMINI_MODEL = "gemini-2.0-flash"

# ============================================================================
# 初始化
# ============================================================================

def init_gemini() -> genai.GenerativeModel:
    """初始化 Gemini 客户端"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def init_supabase() -> Client:
    """初始化 Supabase 客户端"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    
    return create_client(url, key)


def load_feed_config() -> list[dict]:
    """加载 RSS 源配置"""
    config_path = Path(__file__).parent.parent / "config" / "info_map.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("feeds", [])


# ============================================================================
# RSS 抓取
# ============================================================================

def fetch_rss_feed(feed_url: str, limit: int = FETCH_ITEMS_PER_SOURCE) -> list[dict]:
    """
    抓取单个 RSS 源
    
    Returns:
        list of dict with keys: title, url, summary, published
    """
    try:
        feed = feedparser.parse(feed_url)
        items = []
        
        for entry in feed.entries[:limit]:
            # 提取摘要，处理不同的字段名
            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description
            elif hasattr(entry, "content") and entry.content:
                summary = entry.content[0].get("value", "")
            
            # 清理 HTML 标签
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            # 截断过长的摘要
            if len(summary) > 500:
                summary = summary[:500] + "..."
            
            # 提取发布时间
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            
            items.append({
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "summary": summary,
                "published": published.isoformat() if published else None,
            })
        
        return items
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {feed_url}: {e}")
        return []


def fetch_all_feeds(feeds: list[dict]) -> dict[str, list[dict]]:
    """
    抓取所有 RSS 源
    
    Returns:
        dict mapping source name to list of items
    """
    all_items = {}
    
    for feed in feeds:
        name = feed["name"]
        url = feed["url"]
        print(f"Fetching: {name}...")
        
        items = fetch_rss_feed(url)
        if items:
            all_items[name] = items
            print(f"  Found {len(items)} items")
        else:
            print(f"  No items found")
    
    return all_items


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

请以 JSON 格式返回结果，格式如下：
```json
{{
  "selected": [
    {{
      "index": 0,
      "reason": "简短说明为什么选择这篇文章（20字以内）"
    }}
  ]
}}
```

只返回 JSON，不要其他内容。index 是文章在列表中的索引（从 0 开始）。
"""


def filter_items_with_gemini(
    model: genai.GenerativeModel,
    items: list[dict],
    limit: int = MAX_ITEMS_PER_SOURCE
) -> list[dict]:
    """
    使用 Gemini 筛选最相关的文章
    
    Args:
        model: Gemini 模型实例
        items: 原始文章列表
        limit: 最多返回的文章数
    
    Returns:
        筛选后的文章列表，每篇文章增加 ai_reason 字段
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
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # 提取 JSON
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if not json_match:
            print("  [WARN] Could not parse Gemini response, returning original items")
            return items[:limit]
        
        result = json.loads(json_match.group())
        selected_indices = [item["index"] for item in result.get("selected", [])]
        reasons = {item["index"]: item.get("reason", "") for item in result.get("selected", [])}
        
        # 根据索引提取文章
        filtered = []
        for idx in selected_indices:
            if 0 <= idx < len(items):
                item = items[idx].copy()
                item["ai_reason"] = reasons.get(idx, "")
                filtered.append(item)
        
        return filtered[:limit]
    
    except Exception as e:
        print(f"  [ERROR] Gemini filtering failed: {e}")
        return items[:limit]


# ============================================================================
# 数据库操作
# ============================================================================

def ensure_tables_exist(supabase: Client) -> None:
    """确保所需的表存在，如果不存在则跳过日报保存"""
    try:
        # 检查 daily_reports 表是否存在
        supabase.table("daily_reports").select("id").limit(1).execute()
        print("  daily_reports table: OK")
    except Exception:
        print("  [WARN] daily_reports table not found. Daily report will not be saved.")
        print("  To create it, run this SQL in Supabase Dashboard:")
        print("  CREATE TABLE daily_reports (")
        print("    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,")
        print("    report_date DATE DEFAULT CURRENT_DATE UNIQUE,")
        print("    content TEXT NOT NULL,")
        print("    created_at TIMESTAMPTZ DEFAULT NOW()")
        print("  );")


def upsert_hotspots(supabase: Client, items: list[dict], source: str) -> int:
    """
    将热点数据写入 Supabase
    
    使用 url 作为唯一标识进行 upsert
    
    Returns:
        成功写入的记录数
    """
    if not items:
        return 0
    
    records = []
    for item in items:
        records.append({
            "title": item["title"],
            "url": item["url"],
            "summary": item.get("ai_reason") or item.get("summary", ""),
            "source": source,
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


def save_daily_report(supabase: Client, report_content: str) -> bool:
    """保存每日报告到数据库"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    try:
        supabase.table("daily_reports").upsert({
            "report_date": today,
            "content": report_content,
        }, on_conflict="report_date").execute()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save daily report: {e}")
        return False


# ============================================================================
# 报告生成
# ============================================================================

TRANSLATE_PROMPT = """请将以下文章标题翻译成中文。保持简洁，不要添加额外解释。

标题列表：
{titles}

请以 JSON 格式返回翻译结果：
```json
{{
  "translations": [
    "翻译后的标题1",
    "翻译后的标题2"
  ]
}}
```

只返回 JSON，不要其他内容。翻译顺序必须与原标题一一对应。
"""


def translate_titles(model: genai.GenerativeModel, titles: list[str]) -> list[str]:
    """
    使用 Gemini 将标题翻译成中文
    
    Args:
        model: Gemini 模型实例
        titles: 原始标题列表
    
    Returns:
        翻译后的标题列表（失败则返回原标题）
    """
    if not titles:
        return titles
    
    # 构建标题列表
    titles_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])
    prompt = TRANSLATE_PROMPT.format(titles=titles_text)
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # 提取 JSON
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if not json_match:
            print("  [WARN] Could not parse translation response, using original titles")
            return titles
        
        result = json.loads(json_match.group())
        translations = result.get("translations", [])
        
        # 确保翻译数量匹配
        if len(translations) != len(titles):
            print(f"  [WARN] Translation count mismatch ({len(translations)} vs {len(titles)}), using original")
            return titles
        
        return translations
    
    except Exception as e:
        print(f"  [WARN] Translation failed: {e}, using original titles")
        return titles


def generate_daily_report(
    all_selected: dict[str, list[dict]], 
    model: genai.GenerativeModel = None
) -> str:
    """生成每日 Markdown 报告（中文版）"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    lines = [
        f"# AI 热点日报 - {today}",
        "",
        f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
    ]
    
    total_count = sum(len(items) for items in all_selected.values())
    lines.append(f"今日共收录 **{total_count}** 条热点，来自 **{len(all_selected)}** 个信息源。")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for source, items in all_selected.items():
        lines.append(f"## {source}")
        lines.append("")
        
        # 收集所有标题进行批量翻译
        original_titles = [item["title"] for item in items]
        
        if model:
            print(f"  Translating {len(original_titles)} titles for {source}...")
            translated_titles = translate_titles(model, original_titles)
        else:
            translated_titles = original_titles
        
        for i, item in enumerate(items):
            title_cn = translated_titles[i] if i < len(translated_titles) else item["title"]
            url = item["url"]
            reason = item.get("ai_reason", "")
            
            lines.append(f"### {i+1}. [{title_cn}]({url})")
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
    
    # 初始化
    print("[1/5] Initializing...")
    try:
        model = init_gemini()
        supabase = init_supabase()
        feeds = load_feed_config()
        print(f"  Loaded {len(feeds)} feed sources")
        ensure_tables_exist(supabase)
    except Exception as e:
        print(f"[FATAL] Initialization failed: {e}")
        sys.exit(1)
    
    # 抓取所有源
    print()
    print("[2/5] Fetching RSS feeds...")
    raw_data = fetch_all_feeds(feeds)
    
    if not raw_data:
        print("[WARN] No data fetched from any source")
        sys.exit(0)
    
    # 使用 Gemini 筛选
    print()
    print("[3/5] Filtering with Gemini...")
    all_selected = {}
    
    for source, items in raw_data.items():
        print(f"  Processing: {source} ({len(items)} items)")
        selected = filter_items_with_gemini(model, items)
        if selected:
            all_selected[source] = selected
            print(f"    Selected {len(selected)} items")
    
    # 写入数据库
    print()
    print("[4/5] Saving to database...")
    total_saved = 0
    
    for source, items in all_selected.items():
        count = upsert_hotspots(supabase, items, source)
        total_saved += count
        print(f"  {source}: {count} records")
    
    print(f"  Total saved: {total_saved} records")
    
    # 生成并保存报告
    print()
    print("[5/5] Generating daily report...")
    report = generate_daily_report(all_selected, model)
    
    if save_daily_report(supabase, report):
        print("  Daily report saved successfully")
    else:
        print("  [WARN] Failed to save daily report")
    
    # 输出报告预览
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
