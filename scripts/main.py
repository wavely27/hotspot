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

请以 JSON 格式返回结果，**所有文本内容必须翻译成中文**，格式如下：
```json
{{
  "selected": [
    {{
      "index": 0,
      "title_cn": "中文标题",
      "reason_cn": "中文推荐理由（作为该资讯的简短总结，50字以内）"
    }}
  ]
}}
```

只返回 JSON，不要其他内容。index 是文章在列表中的索引（从 0 开始）。
"""

SUMMARY_PROMPT = """请根据以下今日 AI 热点新闻的标题和推荐理由，写一段约 50 字的简短日报综述。
综述应点出今天最值得关注的 1-3 个核心热点事件。

热点列表：
{content}

请直接返回综述文本，不要加任何前缀或格式。
"""


def filter_items_with_gemini(
    model: genai.GenerativeModel,
    items: list[dict],
    limit: int = MAX_ITEMS_PER_SOURCE
) -> list[dict]:
    """
    使用 Gemini 筛选最相关的文章，并生成中文标题和理由
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
        
        selected_map = {item["index"]: item for item in result.get("selected", [])}
        selected_indices = [item["index"] for item in result.get("selected", [])]
        
        # 根据索引提取文章并更新为中文信息
        filtered = []
        for idx in selected_indices:
            if 0 <= idx < len(items):
                item = items[idx].copy()
                gemini_data = selected_map.get(idx, {})
                
                # 使用中文信息覆盖或新增字段
                if gemini_data.get("title_cn"):
                    item["title"] = gemini_data["title_cn"]
                if gemini_data.get("reason_cn"):
                    item["ai_reason"] = gemini_data["reason_cn"]
                
                filtered.append(item)
        
        return filtered[:limit]
    
    except Exception as e:
        print(f"  [ERROR] Gemini filtering failed: {e}")
        # 出错时降级：返回原文前 N 条
        return items[:limit]


def generate_daily_summary(model: genai.GenerativeModel, all_selected: dict[str, list[dict]]) -> str:
    """生成日报整体综述"""
    content = ""
    for source, items in all_selected.items():
        for item in items:
            title = item.get("title", "")
            reason = item.get("ai_reason", "")
            content += f"- {title}: {reason}\n"
    
    if not content:
        return "今日暂无重点资讯。"

    prompt = SUMMARY_PROMPT.format(content=content[:5000]) # 限制长度
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"  [WARN] Failed to generate summary: {e}")
        return "今日 AI 热点资讯汇总。"


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
    """保存每日报告到数据库"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    data = {
        "report_date": today,
        "content": report_content,
        "summary": summary
    }
    
    try:
        supabase.table("daily_reports").upsert(data, on_conflict="report_date").execute()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save daily report: {e}")
        return False


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
            reason = item.get("ai_reason", "") # 已经是中文
            
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
    
    # 初始化
    print("[1/6] Initializing...")
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
    print("[2/6] Fetching RSS feeds...")
    raw_data = fetch_all_feeds(feeds)
    
    if not raw_data:
        print("[WARN] No data fetched from any source")
        sys.exit(0)
    
    # 使用 Gemini 筛选并中文化
    print()
    print("[3/6] Filtering & Translating with Gemini...")
    all_selected = {}
    
    for source, items in raw_data.items():
        print(f"  Processing: {source} ({len(items)} items)")
        selected = filter_items_with_gemini(model, items)
        if selected:
            all_selected[source] = selected
            print(f"    Selected {len(selected)} items")
    
    # 生成日报综述
    print()
    print("[4/6] Generating daily summary...")
    daily_summary = ""
    if all_selected:
        try:
            daily_summary = generate_daily_summary(model, all_selected)
            print(f"  Summary: {daily_summary}")
        except Exception as e:
            print(f"  [WARN] Skipped summary generation: {e}")
    
    # 写入数据库 (Hotspots)
    print()
    print("[5/6] Saving hotspots to database...")
    total_saved = 0
    
    for source, items in all_selected.items():
        count = upsert_hotspots(supabase, items, source)
        total_saved += count
        print(f"  {source}: {count} records")
    
    print(f"  Total saved: {total_saved} records")
    
    # 生成并保存报告 (Daily Report)
    print()
    print("[6/6] Generating & Saving daily report...")
    report = generate_daily_report(all_selected, daily_summary)
    
    if save_daily_report(supabase, report, daily_summary):
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
