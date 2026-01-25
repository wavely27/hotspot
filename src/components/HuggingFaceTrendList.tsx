import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import '../styles/huggingface.css';

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

// Helper to format numbers (e.g. 1.2k)
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
          console.error('Error fetching huggingface trends:', fetchError);
        } else if (data && data.length > 0) {
            setModels(data);
        }
      } catch (e) {
        console.error('Failed to fetch huggingface trends:', e);
      }
    }

    fetchLatest();
  }, []);

  if (error) {
    return (
      <div className="error-message">
        <p>加载失败: {error}</p>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="empty-message">
        <p>暂无趋势数据</p>
      </div>
    );
  }

  return (
    <div className="models-grid">
      {models.map((model) => (
        <a key={model.model_id} href={model.url} target="_blank" rel="noopener noreferrer" className="model-card">
          <div className="card-header">
            <h3 className="model-name" title={model.model_id}>{model.model_id}</h3>
            <div className="metrics">
              <span className="metric" title="Trending Score">
                🔥 {Math.round(model.trending_score)}
              </span>
            </div>
          </div>

          <div className="card-badges">
            {model.pipeline_tag && (
              <span className="badge pipeline-badge">
                {model.pipeline_tag}
              </span>
            )}
            <span className="metric-badge" title="Likes">
              ❤️ {formatNumber(model.likes)}
            </span>
            <span className="metric-badge" title="Downloads">
              ⬇️ {formatNumber(model.downloads)}
            </span>
          </div>
          
          <div className="card-body">
            {model.description_cn && (
              <p className="description">{model.description_cn}</p>
            )}
            
            {model.ai_reason && (
              <div className="ai-reason">
                <span className="reason-icon">💡</span>
                <p>{model.ai_reason}</p>
              </div>
            )}
          </div>

          {model.tags && model.tags.length > 0 && (
            <div className="tags-container">
              {model.tags.slice(0, 5).map(tag => (
                <span key={tag} className="tag">{tag}</span>
              ))}
            </div>
          )}
        </a>
      ))}
    </div>
  );
}
