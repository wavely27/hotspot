import type { APIRoute } from 'astro'
import { supabase } from '../../lib/supabase'

export const GET: APIRoute = async ({ url }) => {
  if (!supabase) {
    return new Response(
      JSON.stringify({
        success: false,
        error: 'Supabase is not configured',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // 获取查询参数
  const limit = parseInt(url.searchParams.get('limit') || '10')

  try {
    const { data, error } = await supabase
      .from('daily_reports')
      .select('*')
      .order('report_date', { ascending: false })
      .limit(limit)

    if (error) {
      return new Response(
        JSON.stringify({
          success: false,
          error: error.message,
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        count: data?.length || 0,
        data,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
  } catch (err) {
    return new Response(
      JSON.stringify({
        success: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
