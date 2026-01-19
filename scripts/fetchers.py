#!/usr/bin/env python3
"""
数据采集器模块

支持多种数据源：
- RSS 订阅源
- HTML 网页爬虫
- API 接口
"""

import re
import json
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_rss_feed(feed_url: str, limit: int = 30) -> list[dict]:
    """抓取 RSS 源"""
    try:
        feed = feedparser.parse(feed_url)
        items = []
        
        for entry in feed.entries[:limit]:
            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description
            elif hasattr(entry, "content") and entry.content:
                summary = entry.content[0].get("value", "")
            
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            if len(summary) > 500:
                summary = summary[:500] + "..."
            
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
        print(f"  [ERROR] Failed to fetch RSS {feed_url}: {e}")
        return []


def fetch_aibase_news(limit: int = 30) -> list[dict]:
    """爬取 AIbase 新闻"""
    url = "https://www.aibase.com/zh/news"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        items = []
        articles = soup.select("article, .news-item, [class*='news'], [class*='article']")
        
        if not articles:
            articles = soup.find_all("a", href=re.compile(r"/news/\d+"))
        
        seen_urls = set()
        for article in articles[:limit * 2]:
            link = article if article.name == "a" else article.find("a")
            if not link:
                continue
                
            href = link.get("href", "")
            if not href or href in seen_urls:
                continue
            
            full_url = urljoin(url, href)
            if "/news/" not in full_url:
                continue
                
            seen_urls.add(href)
            
            title_elem = article.find(["h1", "h2", "h3", "h4"]) or link
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            if not title or len(title) < 5:
                continue
            
            summary_elem = article.find(["p", ".summary", ".desc", ".description"])
            summary = summary_elem.get_text(strip=True) if summary_elem else ""
            
            items.append({
                "title": title,
                "url": full_url,
                "summary": summary[:500] if summary else "",
                "published": None,
            })
            
            if len(items) >= limit:
                break
        
        return items
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch AIbase: {e}")
        return []


def fetch_aibot_daily_news(limit: int = 30) -> list[dict]:
    """爬取 AI工具集 每日资讯"""
    url = "https://ai-bot.cn/daily-ai-news/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        items = []
        news_blocks = soup.find_all(["h3", "h4", "strong"])
        
        for block in news_blocks[:limit * 2]:
            text = block.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            
            parent = block.find_parent(["div", "section", "article"])
            if not parent:
                continue
            
            link = parent.find("a", href=True)
            href = link.get("href") if link else ""
            
            summary_elem = block.find_next(["p", "div"])
            summary = ""
            if summary_elem and summary_elem != block:
                summary = summary_elem.get_text(strip=True)[:500]
            
            items.append({
                "title": text,
                "url": href or url,
                "summary": summary,
                "published": None,
            })
            
            if len(items) >= limit:
                break
        
        return items
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch AI工具集: {e}")
        return []


def fetch_ithome_ai_news(limit: int = 30) -> list[dict]:
    """抓取 IT之家 RSS 并筛选 AI 相关"""
    rss_url = "https://www.ithome.com/rss/"
    ai_keywords = [
        "AI", "人工智能", "大模型", "ChatGPT", "GPT", "LLM", "机器学习",
        "深度学习", "神经网络", "Gemini", "Claude", "OpenAI", "智能",
        "AIGC", "生成式", "Copilot", "智能体", "Agent", "机器人"
    ]
    
    try:
        items = fetch_rss_feed(rss_url, limit=100)
        
        filtered = []
        for item in items:
            text = f"{item['title']} {item['summary']}".upper()
            if any(kw.upper() in text for kw in ai_keywords):
                filtered.append(item)
                if len(filtered) >= limit:
                    break
        
        return filtered
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch IT之家: {e}")
        return []


def fetch_github_trending_ai(limit: int = 30) -> list[dict]:
    """通过 GitHub Search API 获取 AI 相关热门仓库"""
    api_url = "https://api.github.com/search/repositories"
    params = {
        "q": "topic:machine-learning stars:>1000",
        "sort": "updated",
        "order": "desc",
        "per_page": min(limit, 100)
    }
    
    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        items = []
        for repo in data.get("items", [])[:limit]:
            items.append({
                "name": repo["full_name"],
                "url": repo["html_url"],
                "description": repo.get("description") or "",
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo.get("language") or "",
                "topics": repo.get("topics", []),
                "updated_at": repo.get("pushed_at"),
            })
        
        return items
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch GitHub Trending: {e}")
        return []


def fetch_huggingface_trending(limit: int = 30) -> list[dict]:
    """通过 HuggingFace API 获取热门模型"""
    api_url = "https://huggingface.co/api/models"
    params = {
        "sort": "trendingScore",
        "direction": "-1",
        "limit": min(limit, 100)
    }
    
    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        models = resp.json()
        
        items = []
        for model in models[:limit]:
            model_id = model.get("id") or model.get("modelId", "")
            items.append({
                "model_id": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "likes": model.get("likes", 0),
                "downloads": model.get("downloads", 0),
                "trending_score": model.get("trendingScore", 0),
                "pipeline_tag": model.get("pipeline_tag") or "",
                "tags": model.get("tags", []),
                "created_at": model.get("createdAt"),
            })
        
        return items
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch HuggingFace Trending: {e}")
        return []


if __name__ == "__main__":
    print("Testing fetchers...\n")
    
    print("1. AIbase News:")
    items = fetch_aibase_news(5)
    for i, item in enumerate(items, 1):
        print(f"   {i}. {item['title'][:50]}...")
    print(f"   Total: {len(items)}\n")
    
    print("2. AI工具集 Daily News:")
    items = fetch_aibot_daily_news(5)
    for i, item in enumerate(items, 1):
        print(f"   {i}. {item['title'][:50]}...")
    print(f"   Total: {len(items)}\n")
    
    print("3. IT之家 AI News:")
    items = fetch_ithome_ai_news(5)
    for i, item in enumerate(items, 1):
        print(f"   {i}. {item['title'][:50]}...")
    print(f"   Total: {len(items)}\n")
    
    print("4. GitHub Trending AI:")
    items = fetch_github_trending_ai(5)
    for i, item in enumerate(items, 1):
        print(f"   {i}. {item['name']} ⭐{item['stars']}")
    print(f"   Total: {len(items)}\n")
    
    print("5. HuggingFace Trending:")
    items = fetch_huggingface_trending(5)
    for i, item in enumerate(items, 1):
        print(f"   {i}. {item['model_id']} 🔥{item['trending_score']}")
    print(f"   Total: {len(items)}\n")
