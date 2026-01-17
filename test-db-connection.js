#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://puslwtmqlxpxazvppjpm.supabase.co'
const supabaseKey = 'sb_publishable_shfvxntLyffiprOJUq6z8A_TGE50k0P'

const supabase = createClient(supabaseUrl, supabaseKey)

console.log('🔗 Testing Supabase Connection...\n')

async function testConnection() {
  console.log('1. Checking if hotspots table exists...')

  const { data, error } = await supabase
    .from('hotspots')
    .select('*')
    .limit(1)

  if (error) {
    console.log('❌ hotspots table does not exist')
    console.log('\n📋 Ensure "hotspots" table exists in your Supabase database')
    console.log('📌 URL: https://supabase.com/dashboard/project/puslwtmqlxpxazvppjpm/sql/new\n')
    console.log('💡 Alternative: Run this command to open SQL Editor directly:')
    console.log('   open https://supabase.com/dashboard/project/puslwtmqlxpxazvppjpm/sql/new\n')
    return false
  }

  console.log('✅ hotspots table exists!')
  console.log(`📊 Found ${data?.length || 0} records`)
  
  if (data && data.length > 0) {
    console.log('\nSample data:')
    data.forEach((row, idx) => {
      console.log(`   ${idx + 1}. ${row.name} (ID: ${row.id})`)
    })
  }
  
  console.log('\n✅ Database connection successful!')
  console.log('\n🌐 Test your API endpoint:')
  console.log('   http://localhost:4321/api/test-connection\n')
  console.log('🏠 Visit your app:')
  console.log('   http://localhost:4321\n')
  
  return true
}

testConnection()
