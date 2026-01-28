import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Heart, Download, Flame, Lightbulb, Box } from 'lucide-react';

interface HuggingFaceModel {
  model_id: string;
  url: string;
  description_cn?: string;
  likes: number;
  downloads: number;
  trending_score: number;
  pipeline_tag?: string;
  tags?: string[];
  ai_reason?: string;
  fetched_date: string;
}

interface Props {
  initialModels: HuggingFaceModel[];
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

export default function HuggingFaceTrendList({ initialModels }: Props) {
  const [models, setModels] = useState<HuggingFaceModel[]>(initialModels);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLatest() {
      if (!supabase) return;

      try {
        const { data, error: fetchError } = await supabase
          .from('huggingface_trending')
          .select('model_id, url, description_cn, likes, downloads, trending_score, pipeline_tag, tags, ai_reason, fetched_date')
          .order('fetched_date', { ascending: false })
          .order('trending_score', { ascending: false })
          .limit(30);

        if (fetchError) {
          if (initialModels.length === 0) setError(fetchError.message);
        } else if (data && data.length > 0) {
            setModels(data);
        }
      } catch (e) {
        if (initialModels.length === 0) setError(e instanceof Error ? e.message : 'Unknown error');
      }
    }

    fetchLatest();
  }, []);

  if (error) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-slate-200 shadow-sm">
        <p className="text-semantic-error">加载失败: {error}</p>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-slate-200 shadow-sm">
        <p className="text-slate-500">暂无趋势数据</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {models.map((model) => (
        <a 
          key={model.model_id} 
          href={model.url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="group flex flex-col bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-card-hover hover:border-orange-200 transition-all duration-200 h-full"
        >
          <div className="flex justify-between items-start mb-3">
            <h3 className="text-base font-semibold text-slate-900 group-hover:text-orange-600 transition-colors truncate pr-2 flex-1" title={model.model_id}>
              {model.model_id}
            </h3>
            <div className="flex items-center gap-1 bg-orange-50 px-2 py-1 rounded-md text-xs font-medium text-orange-600">
              <Flame size={12} className="fill-orange-500 text-orange-500" />
              {Math.round(model.trending_score)}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-4 text-xs">
            {model.pipeline_tag && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                <Box size={10} />
                {model.pipeline_tag}
              </span>
            )}
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-50 text-slate-500">
              <Heart size={10} /> {formatNumber(model.likes)}
            </span>
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-50 text-slate-500">
              <Download size={10} /> {formatNumber(model.downloads)}
            </span>
          </div>
          
          <div className="flex-grow">
            {model.description_cn && (
              <p className="text-sm text-slate-600 mb-4 line-clamp-2">{model.description_cn}</p>
            )}
            
            {model.ai_reason && (
              <div className="bg-orange-50/50 p-3 rounded-lg mb-4 border border-orange-100">
                <div className="flex gap-2 text-xs text-orange-700 leading-relaxed">
                  <Lightbulb size={14} className="shrink-0 mt-0.5 text-orange-500" />
                  <p>{model.ai_reason}</p>
                </div>
              </div>
            )}
          </div>

          {model.tags && model.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-auto pt-3 border-t border-slate-100">
              {model.tags.slice(0, 4).map(tag => (
                <span key={tag} className="px-1.5 py-0.5 bg-slate-50 text-slate-400 text-[10px] rounded border border-slate-100">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </a>
      ))}
    </div>
  );
}
