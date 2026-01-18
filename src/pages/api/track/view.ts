import type { APIRoute } from 'astro'
import { supabase } from '../../../lib/supabase'

export const POST: APIRoute = async ({ request, clientAddress }) => {
  if (!supabase) {
    return new Response(JSON.stringify({ error: 'Supabase not configured' }), { status: 500 })
  }

  try {
    const body = await request.json()
    const { path, referrer } = body
    
    // 简单的 IP 哈希（实际生产环境可用更严谨的脱敏方式）
    const ipHash = btoa(clientAddress).substring(0, 10)

    const { error } = await supabase.from('page_views').insert({
      path: path || '/',
      referrer: referrer || '',
      user_agent: request.headers.get('user-agent') || '',
      ip_hash: ipHash
    })

    if (error) throw error

    return new Response(JSON.stringify({ success: true }), { status: 200 })
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Failed to track view' }), { status: 500 })
  }
}
