import { supabase } from './supabase'

/**
 * 前端埋点工具 - 直接写入 Supabase (Client Side)
 */

export function trackPageView() {
  if (typeof window === 'undefined' || !supabase) return

  // 简单的 IP 哈希无法在纯前端实现（需要后端），这里简化为记录 UA 和 Referrer
  // 如果需要更精确的统计，建议接入 Google Analytics 或 Cloudflare Analytics
  
  const payload = {
    path: window.location.pathname,
    referrer: document.referrer,
    user_agent: navigator.userAgent
  }

  // 使用 requestIdleCallback 在空闲时发送
  const send = () => {
    if (supabase) {
      supabase.from('page_views').insert(payload).then(({ error }) => {
        if (error) console.error('Track view failed:', error)
      })
    }
  }

  if ('requestIdleCallback' in window) {
    (window as any).requestIdleCallback(send)
  } else {
    setTimeout(send, 1000)
  }
}

export function trackClick(url: string, hotspotId?: string, source?: string) {
  if (!supabase) return

  const payload: Record<string, string> = {
    url,
    source: source || window.location.pathname
  }
  
  if (hotspotId) {
    payload.hotspot_id = hotspotId
  }
  
  supabase.from('hotspot_clicks').insert(payload).then(({ error }) => {
    if (error) console.error('Track click failed:', error)
  })
}
