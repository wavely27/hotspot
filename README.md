# 📅 Hotspot - AI 技术热点日报自动化系统

Hotspot 是一个全流程自动化的 AI 资讯聚合平台。它通过监测全球顶级科技博客，利用 LLM（Gemini）进行深度内容筛选、翻译和总结，自动生成高质量的中文技术日报。

## ✨ 核心亮点

*   **全自动无人值守**：GitHub Actions 每日定时抓取，无需人工干预。
*   **AI 深度筛选**：利用 Google Gemini 模型过滤噪声，只保留高价值技术内容。
*   **智能中文化**：自动翻译标题并生成 50 字以内的中文核心摘要，打破语言障碍。
*   **数据可视化后台**：内置管理面板，监控内容流量与用户点击行为。

## 🏗️ 系统架构

系统分为三个主要层级：数据采集层、数据存储层、应用展示层。

### 1. 数据采集与处理 (Python)
核心脚本位于 `scripts/` 目录：
*   **多源抓取**：支持 RSS/Atom 协议，覆盖 OpenAI, DeepMind, HuggingFace, Reddit 等源。
*   **智能管道**：
    1.  **Fetch**: 获取原始数据 (Feedparser)。
    2.  **Filter**: Gemini 模型识别 AI 相关性，剔除无关内容。
    3.  **Translate**: 同步生成中文标题与推荐理由。
    4.  **Summary**: 生成全篇日报的 50 字核心综述。
*   **限流保护**：内置智能休眠机制，适配免费版 API 的速率限制 (429 错误自动降级)。

### 2. 数据库 (Supabase/PostgreSQL)
*   **`hotspots`**: 存储单条热点资讯（去重入库）。
*   **`daily_reports`**: 存储每日生成的 Markdown 格式日报及综述。
*   **`page_views`**: 记录页面 PV (用于流量分析)。
*   **`hotspot_clicks`**: 记录外链点击行为 (用于热度分析)。

### 3. 前端门户 (Astro + React)
*   **日报门户**：
    *   首页 (`/`)：以时间轴形式展示历史日报，包含核心综述。
    *   详情页 (`/reports/[date]`)：SSR 实时渲染，支持 SEO 优化的完整日报内容。
*   **管理后台** (`/admin`)：
    *   **仪表盘**：使用 Recharts 展示 7 天流量趋势图。
    *   **发布中心**：一键复制 Markdown/HTML 格式日报（适配公众号/知乎）。
    *   **流量分析**：查看详细的访问路径与点击来源。

## 🚀 部署指南

### 环境变量配置
在 `.env` 或服务器环境变量中配置：
```bash
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key # 用于写入数据
SUPABASE_ANON_KEY=your_anon_key                 # 用于前端读取
```

### 数据库初始化
在 Supabase SQL Editor 中依次执行：
1. `scripts/create_daily_reports_table.sql`
2. `scripts/create_analytics_tables.sql`
3. `scripts/update_db_add_summary.sql`

### 自动化配置
项目包含 `.github/workflows/daily_fetch.yml`，默认每天 **UTC 19:00 (北京时间 03:00)** 执行。需在 GitHub Repository Settings 中配置 Secrets。

## 🛠️ 技术栈

*   **Language**: Python 3.11, TypeScript
*   **Framework**: Astro 5 (Static), React 19
*   **UI**: Tailwind CSS 4, Lucide React, Recharts
*   **Database**: Supabase
*   **AI Model**: Google Gemini 2.0 Flash
*   **CI/CD**: GitHub Actions
