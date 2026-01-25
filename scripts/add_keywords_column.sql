-- 为 hotspots 表添加 keywords 字段
-- 执行时间: 2026-01-21

-- 添加 keywords 字段（JSON 数组类型）
ALTER TABLE hotspots 
ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}';

-- 添加注释
COMMENT ON COLUMN hotspots.keywords IS '文章关键词数组，由 LLM 提取的 2-5 个核心关键词';

-- 创建 GIN 索引以支持高效的数组查询
CREATE INDEX IF NOT EXISTS idx_hotspots_keywords ON hotspots USING GIN (keywords);

-- 验证字段是否添加成功
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'hotspots' AND column_name = 'keywords';
