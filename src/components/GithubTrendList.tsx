import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import '../styles/github.css';

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
    // Client-side fetch to update data
    async function fetchLatest() {
      if (!supabase) return;

      try {
        const { data, error: fetchError } = await supabase
          .from('github_trending')
          .select('name, url, description, description_cn, stars, forks, language, topics, ai_reason, fetched_date')
          .order('fetched_date', { ascending: false })
          .order('stars', { ascending: false })
          .limit(30);

        if (fetchError) {
          console.error('Error fetching github trends:', fetchError);
        } else if (data && data.length > 0) {
            // Check if data is newer or different? 
            // For now, just replace it as it is "fresh" from DB
            setRepos(data);
        }
      } catch (e) {
        console.error('Failed to fetch github trends:', e);
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

  if (repos.length === 0) {
    return (
      <div className="empty-message">
        <p>暂无趋势数据</p>
      </div>
    );
  }

  return (
    <div className="repo-grid">
      {repos.map((repo) => (
        <a key={repo.name} href={repo.url} target="_blank" rel="noopener noreferrer" className="repo-card">
          <div className="card-header">
            <h3 className="repo-name">
              <span className="owner">{repo.name.split('/')[0]}</span>
              <span className="divider">/</span>
              <span className="name">{repo.name.split('/')[1] || repo.name}</span>
            </h3>
            <div className="stats-badge">
              <div className="stat">
                <span>⭐</span>
                {formatNumber(repo.stars)}
              </div>
            </div>
          </div>

          <p className="description">
            {repo.description_cn || repo.description || '暂无描述'}
          </p>

          {repo.ai_reason && (
            <div className="ai-insight">
              <span className="ai-icon">🤖</span>
              <p>{repo.ai_reason}</p>
            </div>
          )}

          <div className="topics">
            {repo.topics?.slice(0, 4).map(topic => (
              <span key={topic} className="topic-tag">{topic}</span>
            ))}
          </div>

          <div className="card-footer">
            <div className="language">
              <span 
                className="lang-dot" 
                style={{ backgroundColor: getLanguageColor(repo.language) }}
              ></span>
              {repo.language || 'Unknown'}
            </div>
            <div className="stat-secondary">
              <span>🔀 {formatNumber(repo.forks)}</span>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
