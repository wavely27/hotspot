import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { ExternalLink, Clock } from 'lucide-react';

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
      <div className="text-center py-12 bg-white rounded-xl border border-slate-200 shadow-sm">
        <p className="text-semantic-error">加载失败: {error}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-slate-200 shadow-sm">
        <p className="text-slate-500">暂无相关内容</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <article key={item.id} className="group bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-card-hover hover:border-brand-primary/30 transition-all duration-200">
          <div className="flex items-center gap-3 mb-3 text-xs text-slate-500">
            <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
              {item.source}
            </span>
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {formatDate(item.created_at)}
            </span>
          </div>
          
          <h2 className="text-lg font-bold text-slate-900 mb-2 leading-tight">
            <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:text-brand-primary transition-colors flex items-start gap-2">
              {item.title}
              <ExternalLink size={16} className="opacity-0 group-hover:opacity-100 transition-opacity mt-1 text-slate-400 shrink-0" />
            </a>
          </h2>
          
          {item.summary && <p className="text-slate-600 mb-4 text-sm leading-relaxed">{item.summary}</p>}
          
          <div className="flex flex-wrap gap-2">
            {item.tags?.map(t => {
                const tagStyles: Record<string, string> = {
                    trending: "bg-rose-50 text-rose-600 border-rose-100",
                    tech: "bg-emerald-50 text-emerald-600 border-emerald-100",
                    business: "bg-orange-50 text-orange-600 border-orange-100"
                };
                const style = tagStyles[t] || "bg-slate-50 text-slate-500 border-slate-100";
                
                return (
                  <span key={t} className={`px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
                    {t}
                  </span>
                );
            })}
          </div>
        </article>
      ))}
    </div>
  );
}
