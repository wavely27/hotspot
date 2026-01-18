import os
from supabase import create_client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    exit(1)

supabase = create_client(url, key)

# SQL 脚本内容
sql_script = """
-- 1. 页面访问统计表
CREATE TABLE IF NOT EXISTS page_views (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    path TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_page_views_path ON page_views(path);
CREATE INDEX IF NOT EXISTS idx_page_views_created_at ON page_views(created_at);

-- 2. 热点点击统计表
CREATE TABLE IF NOT EXISTS hotspot_clicks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    hotspot_id UUID,
    url TEXT NOT NULL,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hotspot_clicks_hotspot_id ON hotspot_clicks(hotspot_id);
CREATE INDEX IF NOT EXISTS idx_hotspot_clicks_created_at ON hotspot_clicks(created_at);
"""

print("Executing SQL script to create analytics tables...")

try:
    # 尝试使用 Supabase 的 RPC 执行 SQL (需要数据库有一个 exec_sql 函数)
    # 如果没有 exec_sql 函数，通常无法通过 client 直接执行 DDL
    # 但我们可以尝试直接 rest 调用（如果 policy 允许，虽然通常不允许）
    
    # 既然 service_role key 权限很高，我们试试能不能直接调 postgres 接口? 
    # 不行，supabase-py client 只能调 postgrest api。
    # 除非我们在数据库里预置了一个 run_sql 函数。
    
    # 退而求其次，我们提示用户手动执行 SQL，或者假设用户已经有一个 run_sql 函数。
    # 为了保险，我们还是生成 SQL 文件让用户去控制台执行。
    
    print("\n[WARN] 自动建表需要数据库中有 `exec_sql` 函数。")
    print("请复制以下 SQL 到 Supabase SQL Editor 执行：")
    print("-" * 50)
    print(sql_script)
    print("-" * 50)

except Exception as e:
    print(f"Error: {e}")
