import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

interface Hotspot {
  id: string;
  title: string;
  url: string;
  summary: string;
  source: string;
  created_at: string;
  tags: string[];
  duplicate_group?: string;
  is_primary?: boolean;
}

interface Props {
  tag: string;
  initialItems: Hotspot[];
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  
  if (hours < 24) {
    return `${hours} 小时前`;
  }
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

export default function TagFeedList({ tag, initialItems }: Props) {
  const [items, setItems] = useState<Hotspot[]>(initialItems);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLatest() {
      if (!supabase) return;

      try {
        const { data, error: fetchError } = await supabase
          .from('hotspots')
          .select('*')
          .contains('tags', [tag])
          .eq('is_primary', true)
          .order('created_at', { ascending: false })
          .limit(50);

         if (fetchError) {
             // Don't show error to user if we have initial items, just log it
             if (initialItems.length === 0) setError(fetchError.message);
         } else if (data) {
            setItems(data);
         }
       } catch (e) {
         if (initialItems.length === 0) setError(e instanceof Error ? e.message : 'Unknown error');
      }
    }

    fetchLatest();
  }, [tag]);

  if (error) {
    return (
      <div className="error-message">
        <p>加载失败: {error}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="empty-message">
        <p>暂无相关内容</p>
      </div>
    );
  }

  return (
    <div className="feed-list">
      {items.map((item) => (
        <article key={item.id} className="feed-item">
          <div className="item-meta">
            <span className="source-tag">{item.source}</span>
            <time>{formatDate(item.created_at)}</time>
          </div>
          <h2>
            <a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a>
          </h2>
          {item.summary && <p className="summary">{item.summary}</p>}
          <div className="item-tags">
            {item.tags?.map(t => (
              <span key={t} className={`tag ${t}`}>{t}</span>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
