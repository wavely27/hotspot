-- 为 daily_reports 表添加 summary 字段
-- 用于存储日报的简短综述（50字左右）

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'daily_reports' AND column_name = 'summary'
    ) THEN
        ALTER TABLE daily_reports ADD COLUMN summary TEXT;
        COMMENT ON COLUMN daily_reports.summary IS '日报简短综述（中文）';
    END IF;
END $$;
