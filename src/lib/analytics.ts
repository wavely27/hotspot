/**
 * 前端埋点工具
 */

export function trackPageView() {
  if (typeof window === 'undefined') return

  // 避免在本地开发环境发送过多请求（可选）
  // if (window.location.hostname === 'localhost') return

  const payload = {
    path: window.location.pathname,
    referrer: document.referrer
  }

  // 使用 sendBeacon 保证页面关闭时也能发送（如果支持）
  // 这里为了简单使用 fetch，并在空闲时执行
  if ('requestIdleCallback' in window) {
    (window as any).requestIdleCallback(() => sendTrack('/api/track/view', payload))
  } else {
    setTimeout(() => sendTrack('/api/track/view', payload), 1000)
  }
}

export function trackClick(url: string, hotspotId?: string, source?: string) {
  const payload = {
    url,
    hotspot_id: hotspotId,
    source: source || window.location.pathname
  }
  
  // 点击通常伴随跳转，使用 sendBeacon 更可靠
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/track/click', JSON.stringify(payload))
  } else {
    fetch('/api/track/click', {
      method: 'POST',
      body: JSON.stringify(payload),
      keepalive: true
    }).catch(console.error)
  }
}

function sendTrack(endpoint: string, data: any) {
  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).catch(e => console.error('Tracking failed:', e))
}
