-- ============================================================
-- 创建统计分析表
-- 用于存储页面访问量和热点点击量
-- ============================================================

-- 1. 页面访问统计表
CREATE TABLE IF NOT EXISTS page_views (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    path TEXT NOT NULL,           -- 访问路径，如 /reports/2024-01-01
    referrer TEXT,                -- 来源页面
    user_agent TEXT,              -- 用户代理
    ip_hash TEXT,                 -- 简单的 IP 哈希（隐私保护）
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 添加索引以加速查询
CREATE INDEX IF NOT EXISTS idx_page_views_path ON page_views(path);
CREATE INDEX IF NOT EXISTS idx_page_views_created_at ON page_views(created_at);

-- 2. 热点点击统计表
CREATE TABLE IF NOT EXISTS hotspot_clicks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hotspot_id UUID NOT NULL,     -- 关联的热点 ID
    url TEXT NOT NULL,            -- 点击的目标 URL
    source TEXT,                  -- 来源页面，如 daily_report
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_hotspot_clicks_hotspot_id ON hotspot_clicks(hotspot_id);
CREATE INDEX IF NOT EXISTS idx_hotspot_clicks_created_at ON hotspot_clicks(created_at);

-- 添加注释
COMMENT ON TABLE page_views IS '页面访问统计';
COMMENT ON TABLE hotspot_clicks IS '热点外链点击统计';
