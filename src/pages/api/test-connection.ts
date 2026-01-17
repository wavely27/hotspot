import type { APIRoute } from 'astro'
import { supabase } from '../../lib/supabase'

export const GET: APIRoute = async () => {
  if (!supabase) {
    return new Response(
      JSON.stringify({
        success: false,
        error: 'Supabase is not configured',
        hint: 'Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }

  try {
    const { data, error } = await supabase
      .from('hotspots')
      .select('*')
      .limit(10)

    if (error) {
      return new Response(
        JSON.stringify({
          success: false,
          error: error.message,
          hint: 'Ensure the "hotspots" table exists in Supabase'
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Successfully connected to Supabase',
        table: 'hotspots',
        count: data?.length || 0,
        data
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
  } catch (err) {
    return new Response(
      JSON.stringify({
        success: false,
        error: err instanceof Error ? err.message : 'Unknown error occurred'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
