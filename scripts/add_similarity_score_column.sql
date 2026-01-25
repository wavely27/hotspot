-- 为 hotspots 表添加 similarity_score 字段
-- 执行时间: 2026-01-25

-- 添加 similarity_score 字段（浮点数类型，默认为 0）
ALTER TABLE hotspots 
ADD COLUMN IF NOT EXISTS similarity_score FLOAT DEFAULT 0;

-- 添加注释
COMMENT ON COLUMN hotspots.similarity_score IS '与主条目的相似度分数 (0.0-1.0)';

-- 验证字段是否添加成功
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'hotspots' AND column_name = 'similarity_score';
