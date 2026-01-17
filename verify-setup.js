#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://puslwtmqlxpxazvppjpm.supabase.co'
const supabaseKey = 'sb_publishable_shfvxntLyffiprOJUq6z8A_TGE50k0P'

const supabase = createClient(supabaseUrl, supabaseKey)

console.log('🔍 Full Database Connection Test\n')
console.log('=' .repeat(50))

async function fullTest() {
  console.log('\n📡 Step 1: Testing connection to Supabase...')
  
  try {
      const { data, error } = await supabase
      .from('hotspots')
      .select('*')
      .limit(10)
    
    if (error) {
      console.log('❌ Connection failed:', error.message)
      
      if (error.message.includes('Could not find')) {
        console.log('\n💡 Table does not exist. Please create it first:')
        console.log('   1. Visit: https://supabase.com/dashboard/project/puslwtmqlxpxazvppjpm/sql/new')
        console.log('   2. Ensure "hotspots" table exists in your database')
        console.log('   3. Then run this test again')
      }
      return false
    }
    
    console.log('✅ Connection successful!')
    
  console.log('\n📊 Step 2: Fetching data from hotspots table...')
  console.log(`   Found ${data?.length || 0} records`)
    
    if (data && data.length > 0) {
      console.log('\n📝 Sample records:')
      data.slice(0, 5).forEach((row, idx) => {
        const date = new Date(row.created_at).toLocaleString()
        console.log(`   ${idx + 1}. "${row.title || 'Untitled'}"`)
        console.log(`      ID: ${row.id}`)
        console.log(`      URL: ${row.url || 'N/A'}`)
        console.log(`      Status: ${row.is_published ? 'Published' : 'Draft'}`)
        console.log(`      Created: ${date}`)
      })
    } else {
      console.log('   ⚠️  Table exists but is empty')
    }
    
    console.log('\n🌐 Step 3: Testing API endpoint...')
    console.log('   Endpoint: http://localhost:4321/api/test-connection')
    
    const response = await fetch('http://localhost:4321/api/test-connection')
    const apiResult = await response.json()
    
    if (apiResult.success) {
      console.log('✅ API endpoint working!')
      console.log(`   Records returned: ${apiResult.count}`)
    } else {
      console.log('❌ API endpoint failed:', apiResult.error)
      return false
    }
    
    console.log('\n' + '='.repeat(50))
    console.log('✅ ALL TESTS PASSED!')
    console.log('\n🎉 Your Supabase integration is fully functional!')
    console.log('\n🚀 Next steps:')
    console.log('   1. Visit http://localhost:4321')
    console.log('   2. Click "Fetch Data from Supabase" button')
    console.log('   3. See your database data displayed in the UI')
    
    return true
    
  } catch (err) {
    console.log('\n❌ Unexpected error:', err.message)
    return false
  }
}

fullTest()
