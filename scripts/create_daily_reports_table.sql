-- ============================================================
-- 创建 daily_reports 表
-- 用于存储每日 AI 热点汇总报告
-- 
-- 使用方法：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 复制粘贴以下内容并执行
-- ============================================================

-- 创建 daily_reports 表
CREATE TABLE IF NOT EXISTS daily_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_date DATE DEFAULT CURRENT_DATE UNIQUE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 添加表注释
COMMENT ON TABLE daily_reports IS 'AI 热点每日汇总报告';
COMMENT ON COLUMN daily_reports.report_date IS '报告日期（唯一）';
COMMENT ON COLUMN daily_reports.content IS '报告内容（Markdown 格式）';

-- 为 hotspots 表添加 url 唯一约束（如果不存在）
-- 用于支持 upsert 操作的冲突检测
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'hotspots_url_unique'
    ) THEN
        ALTER TABLE hotspots ADD CONSTRAINT hotspots_url_unique UNIQUE (url);
    END IF;
END $$;
