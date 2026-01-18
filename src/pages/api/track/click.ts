import type { APIRoute } from 'astro'
import { supabase } from '../../../lib/supabase'

export const POST: APIRoute = async ({ request }) => {
  if (!supabase) {
    return new Response(JSON.stringify({ error: 'Supabase not configured' }), { status: 500 })
  }

  try {
    const body = await request.json()
    const { hotspot_id, url, source } = body

    if (!url) {
      return new Response(JSON.stringify({ error: 'Missing URL' }), { status: 400 })
    }

    // hotspot_id 是可选的，如果是外部链接可能没有 ID
    const { error } = await supabase.from('hotspot_clicks').insert({
      hotspot_id: hotspot_id || null, // 如果有 UUID 则记录，否则为空
      url,
      source: source || 'unknown'
    })

    if (error) {
       // 忽略外键约束错误（如果 UUID 无效）
       console.error('Click track error:', error)
    }

    return new Response(JSON.stringify({ success: true }), { status: 200 })
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Failed to track click' }), { status: 500 })
  }
}
