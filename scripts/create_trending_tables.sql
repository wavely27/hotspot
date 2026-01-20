-- GitHub Trending AI 项目表
CREATE TABLE IF NOT EXISTS github_trending (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    description_cn TEXT,
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    language TEXT,
    topics TEXT[],
    ai_reason TEXT,
    is_published BOOLEAN DEFAULT TRUE,
    fetched_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_github_trending_date ON github_trending(fetched_date);
CREATE INDEX IF NOT EXISTS idx_github_trending_stars ON github_trending(stars DESC);

-- HuggingFace Trending 模型表
CREATE TABLE IF NOT EXISTS huggingface_trending (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    model_id TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description_cn TEXT,
    likes INTEGER DEFAULT 0,
    downloads INTEGER DEFAULT 0,
    trending_score INTEGER DEFAULT 0,
    pipeline_tag TEXT,
    tags TEXT[],
    ai_reason TEXT,
    is_published BOOLEAN DEFAULT TRUE,
    fetched_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_huggingface_trending_date ON huggingface_trending(fetched_date);
CREATE INDEX IF NOT EXISTS idx_huggingface_trending_score ON huggingface_trending(trending_score DESC);

-- 更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_github_trending_updated_at ON github_trending;
CREATE TRIGGER update_github_trending_updated_at
    BEFORE UPDATE ON github_trending
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_huggingface_trending_updated_at ON huggingface_trending;
CREATE TRIGGER update_huggingface_trending_updated_at
    BEFORE UPDATE ON huggingface_trending
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
