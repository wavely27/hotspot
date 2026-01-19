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
        # AIbase 结构：链接包含 /news/
        article_links = soup.select("a[href*='/news/']")
        
        seen_urls = set()
        
        for link in article_links:
            href = link.get("href", "")
            if not href or href in seen_urls:
                continue
            
            # 排除非新闻详情页
            if not re.search(r"/news/\d+", href):
                continue
                
            full_url = urljoin(url, href)
            seen_urls.add(href)
            
            # 获取标题并清理
            raw_title = link.get_text(strip=True)
            if not raw_title:
                continue
            
            # 清理 "刚刚.AIbase" 等前缀
            # 通常格式是 "时间.作者标题"
            # 我们移除 .AIbase 之前的内容
            title = re.sub(r'^.*\.AIbase', '', raw_title).strip()
            # 如果正则没匹配到（格式不同），直接用原标题
            if not title:
                title = raw_title
                
            # 摘要：AIbase 列表页摘要是 JS 加载的 ("加载中...")
            # 我们直接使用标题作为摘要，或者让 LLM 后续自行生成
            summary = title 
            
            items.append({
                "title": title,
                "url": full_url,
                "summary": summary,
                "published": None,
            })
            
            if len(items) >= limit:
                break
        
        return items
    
    except Exception as e:
        print(f"  [ERROR] Failed to fetch AIbase: {e}")
        return []


def fetch_aibot_daily_news(limit: int = 30) -> list[dict]:
    """爬取 AI工具集 (ai-bot.cn/daily-ai-news/)"""
    url = "https://ai-bot.cn/daily-ai-news/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        items = []
        # 根据 Debug 结果：标题在 h2 中，父容器 class 为 news-content
        # 有时候是 h2 (单条新闻)，有时候是 h3
        news_items = soup.find_all(class_="news-content")
        
        if not news_items:
            # 备用：查找所有 h2
            news_items = soup.find_all("h2")
            
        for container in news_items:
            # 如果 container 是 div.news-content，找里面的 h2
            if container.name == "div":
                title_elem = container.find(["h2", "h3"])
                # 找链接
                link_elem = container.find("a", href=True) or container.find_parent("a")
                # 找摘要
                desc_elem = container.find("p")
            else:
                # container 本身就是 h2
                title_elem = container
                link_elem = container.find("a", href=True)
                desc_elem = container.find_next("p")
            
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 5:
                continue
                
            # 链接
            item_url = url
            if link_elem:
                item_url = link_elem["href"]
            
            # 摘要
            summary = ""
            if desc_elem:
                summary = desc_elem.get_text(strip=True)
            if not summary:
                summary = title
                
            items.append({
                "title": title,
                "url": item_url,
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
    """抓取 IT之家 AI 标签页 (替代 RSS 过滤)"""
    url = "https://www.ithome.com/tag/ai"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        items = []
        # 列表项通常在 .run_list li 或 .news-list li
        list_items = soup.select(".block li, .news-list li, ul.bl li")
        
        seen_urls = set()
        
        for li in list_items:
            # 查找链接
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
                
            href = a_tag["href"]
            if href in seen_urls:
                continue
            
            full_url = href # IT之家通常是完整链接
            if not full_url.startswith("http"):
                full_url = urljoin("https://www.ithome.com", href)
                
            seen_urls.add(href)
            
            # 标题
            title = a_tag.get_text(strip=True)
            # 有时候标题在 h2 或 inside div
            if not title:
                title_elem = li.find(["h2", "h3", ".title"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            if not title:
                continue
                
            # 摘要
            summary = ""
            desc_elem = li.find(class_="memo") or li.find(class_="m")
            if desc_elem:
                summary = desc_elem.get_text(strip=True)
            
            # 时间
            published = None
            date_elem = li.find(class_="time") or li.find(class_="t")
            # 处理时间字符串... 这里简化，由后续流程处理
            
            items.append({
                "title": title,
                "url": full_url,
                "summary": summary,
                "published": None,
            })
            
            if len(items) >= limit:
                break
        
        return items
    
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
