-- ============================================================
-- 数据库迁移：添加标签系统和深度分析功能
-- 
-- 使用方法：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 复制粘贴以下内容并执行
-- ============================================================

-- 1. hotspots 表添加 tags 字段（多标签：trending/tech/business）
ALTER TABLE hotspots ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- 2. hotspots 表添加重复检测相关字段
ALTER TABLE hotspots ADD COLUMN IF NOT EXISTS duplicate_group TEXT;
ALTER TABLE hotspots ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT TRUE;

-- 3. 创建索引加速标签查询
CREATE INDEX IF NOT EXISTS idx_hotspots_tags ON hotspots USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_hotspots_duplicate_group ON hotspots(duplicate_group);

-- 4. 创建 daily_analysis 表 - 存储每日 AI 深度分析
CREATE TABLE IF NOT EXISTS daily_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    
    -- 今日焦点事件（JSON 数组）
    -- 结构: [{ title, summary, why, impact, sources: [] }]
    focus_events JSONB NOT NULL DEFAULT '[]',
    
    -- 整体分析综述
    overview TEXT,
    
    -- 关键词统计（JSON 对象）
    -- 结构: { "keyword": count, ... }
    keywords JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. daily_analysis 更新触发器
DROP TRIGGER IF EXISTS update_daily_analysis_updated_at ON daily_analysis;
CREATE TRIGGER update_daily_analysis_updated_at
    BEFORE UPDATE ON daily_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 6. 添加表注释
COMMENT ON TABLE daily_analysis IS '每日 AI 深度分析';
COMMENT ON COLUMN daily_analysis.focus_events IS '今日焦点事件列表（JSON）';
COMMENT ON COLUMN daily_analysis.overview IS '整体分析综述';
COMMENT ON COLUMN daily_analysis.keywords IS '关键词热度统计';
COMMENT ON COLUMN hotspots.tags IS '分类标签：trending(热点速览)/tech(技术前沿)/business(商业洞察)';
COMMENT ON COLUMN hotspots.duplicate_group IS '重复分组ID，相同事件的热点共享同一ID';
COMMENT ON COLUMN hotspots.is_primary IS '是否为重复组的主条目';
