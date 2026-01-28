import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Star, GitFork, Sparkles } from 'lucide-react';

interface GithubRepo {
  name: string;
  url: string;
  description?: string;
  description_cn?: string;
  stars: number;
  forks: number;
  language?: string;
  topics?: string[];
  ai_reason?: string;
  fetched_date: string;
}

interface Props {
  initialRepos: GithubRepo[];
}

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

function getLanguageColor(lang?: string): string {
  const colors: Record<string, string> = {
    'Python': '#3572A5',
    'TypeScript': '#2b7489',
    'JavaScript': '#f1e05a',
    'Jupyter Notebook': '#DA5B0B',
    'C++': '#f34b7d',
    'Java': '#b07219',
    'Go': '#00ADD8',
    'Rust': '#dea584'
  };
  return colors[lang || ''] || '#8b949e';
}

export default function GithubTrendList({ initialRepos }: Props) {
  const [repos, setRepos] = useState<GithubRepo[]>(initialRepos);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLatest() {
      if (!supabase) return;

      try {
        const { data, error: fetchError } = await supabase
          .from('github_trending')
          .select('name, url, description, description_cn, stars, forks, language, topics, ai_reason, fetched_date')
          .order('fetched_date', { ascending: false })
          .order('stars', { ascending: false })
          .limit(30);

        if (!fetchError && data && data.length > 0) {
          setRepos(data);
        }
      } catch (e) {
        // Keep initial data on error
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

  if (repos.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-slate-200 shadow-sm">
        <p className="text-slate-500">暂无趋势数据</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {repos.map((repo) => (
        <a 
          key={repo.name} 
          href={repo.url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="group flex flex-col bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-card-hover hover:border-brand-primary/30 transition-all duration-200 h-full"
        >
          <div className="flex justify-between items-start mb-3">
            <h3 className="text-base font-semibold text-slate-900 group-hover:text-brand-primary transition-colors truncate pr-2 flex-1">
              <span className="text-slate-500 font-normal">{repo.name.split('/')[0]}</span>
              <span className="mx-1 text-slate-300">/</span>
              {repo.name.split('/')[1] || repo.name}
            </h3>
            <div className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md text-xs font-medium text-slate-700">
              <Star size={12} className="text-amber-500 fill-amber-500" />
              {formatNumber(repo.stars)}
            </div>
          </div>

          <p className="text-sm text-slate-600 mb-4 line-clamp-2 flex-grow">
            {repo.description_cn || repo.description || '暂无描述'}
          </p>

          {repo.ai_reason && (
            <div className="bg-brand-primary/5 p-3 rounded-lg mb-4 border border-brand-primary/10">
              <div className="flex gap-2 text-xs text-brand-primary leading-relaxed">
                <Sparkles size={14} className="shrink-0 mt-0.5" />
                <p>{repo.ai_reason}</p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2 mb-4">
            {repo.topics?.slice(0, 3).map(topic => (
              <span key={topic} className="px-2 py-0.5 bg-slate-50 text-slate-500 text-xs rounded-full border border-slate-100">
                {topic}
              </span>
            ))}
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 mt-auto pt-3 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <span 
                className="w-2.5 h-2.5 rounded-full" 
                style={{ backgroundColor: getLanguageColor(repo.language) }}
              ></span>
              {repo.language || 'Unknown'}
            </div>
            <div className="flex items-center gap-1">
              <GitFork size={12} />
              {formatNumber(repo.forks)}
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
