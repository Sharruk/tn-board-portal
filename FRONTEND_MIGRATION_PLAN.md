# Frontend Migration Plan
## Axios + FastAPI → @supabase/supabase-js

---

## Package Changes

### Add
```bash
npm install @supabase/supabase-js
```

### Remove (optional cleanup)
```bash
npm uninstall axios
```

> `axios` can be removed once all service files are migrated. It is the only runtime dependency being replaced.

---

## New File: `frontend/src/lib/supabase.js`

This is the single Supabase client instance shared across the entire app.

```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY env vars')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

Required `.env.local` for development:
```
VITE_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## File-by-File Migration

---

### `frontend/src/services/api.js` — DELETE

This file exports an Axios instance. Replace entirely with `lib/supabase.js`.
No pages import this file directly — they import from the individual service files.

---

### `frontend/src/services/classes.js` — REPLACE

**Before:**
```javascript
import api from './api'
export const getClasses = () => api.get('/classes')
export const getClass = (id) => api.get(`/classes/${id}`)
export const getSubjectsForClass = (id) => api.get(`/classes/${id}/subjects`)
```

**After:**
```javascript
import { supabase } from '../lib/supabase'

export const getClasses = async () => {
  const { data, error } = await supabase
    .from('classes')
    .select('*, subjects(count)')
    .order('id')
  if (error) throw error
  return { data: data.map(c => ({ ...c, subject_count: c.subjects[0].count })) }
}

export const getClass = async (id) => {
  const { data, error } = await supabase
    .from('classes')
    .select('*, subjects(count)')
    .eq('id', id)
    .single()
  if (error) throw error
  return { data: { ...data, subject_count: data.subjects[0].count } }
}

export const getSubjectsForClass = async (id) => {
  const { data, error } = await supabase
    .from('subjects')
    .select(`
      id, name, slug, is_practical, display_order, class_id,
      classes(name),
      papers(count)
    `)
    .eq('class_id', id)
    .eq('papers.is_visible', true)
    .order('display_order')
  if (error) throw error
  return {
    data: data.map(s => ({
      ...s,
      class_name: s.classes?.name,
      paper_count: s.papers[0]?.count ?? 0,
    }))
  }
}
```

---

### `frontend/src/services/subjects.js` — REPLACE

**Before:**
```javascript
import api from './api'
export const getSubject = (id) => api.get(`/subjects/${id}`)
export const getPapersForSubject = (id, params = {}) =>
  api.get(`/subjects/${id}/papers`, { params })
```

**After:**
```javascript
import { supabase } from '../lib/supabase'

export const getSubject = async (id) => {
  const { data, error } = await supabase
    .from('subjects')
    .select('*, classes(name, slug)')
    .eq('id', id)
    .single()
  if (error) throw error
  return { data: { ...data, class_name: data.classes?.name } }
}

export const getPapersForSubject = async (id, params = {}) => {
  let query = supabase
    .from('papers')
    .select('*')
    .eq('subject_id', id)
    .eq('is_visible', true)
    .order('year', { ascending: false })
  if (params.exam_type) query = query.eq('exam_type', params.exam_type)
  if (params.paper_type) query = query.eq('paper_type', params.paper_type)
  const { data, error } = await query
  if (error) throw error
  return { data }
}
```

---

### `frontend/src/services/papers.js` — REPLACE

**Before:**
```javascript
import api from './api'
export const getPaper = (id) => api.get(`/papers/${id}`)
export const getPaperBySlug = (slug) => api.get(`/papers/by-slug/${slug}`)
export const getRecentPapers = (limit = 10) => api.get('/papers/recent', { params: { limit } })
export const getPopularPapers = (limit = 10) => api.get('/papers/popular', { params: { limit } })
export const getExamTypes = () => api.get('/exam-types')
export const recordDownload = (id) => api.post(`/papers/${id}/download`)
```

**After:**
```javascript
import { supabase } from '../lib/supabase'

export const EXAM_TYPES = [
  'Unit Test 1', 'Unit Test 2', 'Unit Test 3',
  'Quarterly Exam', 'Half Yearly Exam',
  'Annual Exam', 'Public Exam',
  'Practical Exam', 'Model Exam',
]

export const getPaper = async (id) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*, subjects(*, classes(*))')
    .eq('id', id)
    .eq('is_visible', true)
    .single()
  if (error) throw error
  return { data }
}

export const getPaperBySlug = async (slug) => {
  const parts = slug.split('-')
  const id = parseInt(parts[parts.length - 1])
  if (isNaN(id)) throw new Error('Paper not found')
  return getPaper(id)
}

export const getRecentPapers = async (limit = 10) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .eq('is_visible', true)
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return { data }
}

export const getPopularPapers = async (limit = 10) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .eq('is_visible', true)
    .order('download_count', { ascending: false })
    .limit(limit)
  if (error) throw error
  return { data }
}

export const getExamTypes = () =>
  Promise.resolve({ data: { exam_types: EXAM_TYPES } })

export const recordDownload = async (id) => {
  const { error } = await supabase.rpc('increment_download_count', { paper_id_param: id })
  if (error) throw error
}
```

---

### `frontend/src/services/search.js` — REPLACE

**Before:**
```javascript
import api from './api'
export const searchPapers = (params) => api.get('/search', { params })
```

**After:**
```javascript
import { supabase } from '../lib/supabase'

const SUBJECT_ALIASES = {
  maths: 'mathematics', math: 'mathematics', phy: 'physics',
  chem: 'chemistry', bio: 'biology', sci: 'science',
  eng: 'english', eco: 'economics', cs: 'computer science',
}

function expandQuery(q) {
  const normalized = q.trim().toLowerCase()
  const terms = [normalized]
  for (const word of normalized.split(' ')) {
    if (SUBJECT_ALIASES[word] && !terms.includes(SUBJECT_ALIASES[word])) {
      terms.push(SUBJECT_ALIASES[word])
    }
  }
  return terms
}

export const searchPapers = async ({ q, class_id, exam_type, paper_type } = {}) => {
  const terms = expandQuery(q || '')
  const likeConditions = terms.flatMap(t => [
    `title.ilike.%${t}%`,
    `exam_type.ilike.%${t}%`,
  ]).join(',')

  let query = supabase
    .from('papers')
    .select('*, subjects!inner(name, class_id, classes!inner(name))')
    .eq('is_visible', true)
    .or(likeConditions)
    .order('created_at', { ascending: false })
    .limit(50)

  if (class_id) query = query.eq('subjects.class_id', class_id)
  if (exam_type) query = query.eq('exam_type', exam_type)
  if (paper_type) query = query.eq('paper_type', paper_type)

  const { data, error } = await query
  if (error) throw error

  // Log search to analytics table (fire-and-forget)
  supabase.from('search_queries').insert({ term: q, result_count: data.length }).then(() => {})

  return {
    data: {
      query: q,
      total: data.length,
      results: data.map(p => ({
        id: p.id, title: p.title, exam_type: p.exam_type, year: p.year,
        paper_type: p.paper_type, public_url: p.public_url,
        subject_name: p.subjects?.name,
        class_name: p.subjects?.classes?.name,
        slug: `${p.title.toLowerCase().replace(/\s+/g, '-')}-${p.id}`,
      }))
    }
  }
}
```

---

### `frontend/src/services/admin.js` — REPLACE

**Before:** All functions use `adminApi` (Axios with Bearer token).

**After:**
```javascript
import { supabase } from '../lib/supabase'

export const adminLogin = async (email, password) => {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return { data }
}

export const getAdminPapers = async () => {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .order('created_at', { ascending: false })
  if (error) throw error
  return { data }
}

export const uploadPaper = async (formData, onProgress) => {
  const file = formData.get('file')
  const ext = file.name.split('.').pop().toLowerCase()
  const storedFilename = `${crypto.randomUUID()}.${ext}`

  const { error: uploadError } = await supabase.storage
    .from('papers')
    .upload(storedFilename, file, { contentType: 'application/pdf', upsert: false })
  if (uploadError) throw uploadError

  const { data: { publicUrl } } = supabase.storage.from('papers').getPublicUrl(storedFilename)

  const metadata = {
    subject_id: parseInt(formData.get('subject_id')),
    exam_type: formData.get('exam_type'),
    year: parseInt(formData.get('year')),
    title: formData.get('title'),
    paper_type: formData.get('paper_type'),
    youtube_url: formData.get('youtube_url') || null,
    file_path: storedFilename,
    public_url: publicUrl,
    is_visible: true,
  }

  const { data, error } = await supabase.from('papers').insert(metadata).select().single()
  if (error) throw error

  // Log to audit_logs
  const { data: { user } } = await supabase.auth.getUser()
  await supabase.from('audit_logs').insert({
    admin_id: user.id,
    admin_email: user.email,
    action: formData.get('is_bulk') === 'true' ? 'bulk_upload' : 'upload',
    target_paper_id: data.id,
    target_details: { title: data.title, exam_type: data.exam_type, year: data.year },
  })

  return { data }
}

export const updatePaper = async (id, updates) => {
  const { data, error } = await supabase
    .from('papers').update(updates).eq('id', id).select().single()
  if (error) throw error
  const { data: { user } } = await supabase.auth.getUser()
  await supabase.from('audit_logs').insert({
    admin_id: user.id, admin_email: user.email,
    action: 'edit', target_paper_id: id,
    target_details: { changes: updates },
  })
  return { data }
}

export const deletePaper = async (id) => {
  const { data: paper } = await supabase
    .from('papers').select('file_path, title').eq('id', id).single()

  if (paper?.file_path) {
    await supabase.storage.from('papers').remove([paper.file_path])
  }

  const { error } = await supabase.from('papers').delete().eq('id', id)
  if (error) throw error

  const { data: { user } } = await supabase.auth.getUser()
  await supabase.from('audit_logs').insert({
    admin_id: user.id, admin_email: user.email,
    action: 'delete', target_paper_id: id,
    target_details: { title: paper?.title },
  })
}

export const getAdminStats = async () => {
  const { data, error } = await supabase.rpc('get_admin_stats')
  if (error) throw error
  return { data: data[0] }
}

export const getSearchAnalytics = async () => {
  const { data, error } = await supabase.rpc('get_search_analytics')
  if (error) throw error
  return { data }
}

export const getRecentUploads = async (limit = 20) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*, subjects(name, classes(name))')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return {
    data: data.map(p => ({
      ...p,
      subject_name: p.subjects?.name,
      class_name: p.subjects?.classes?.name,
    }))
  }
}

export const getContentStatus = async () => {
  const { data, error } = await supabase.rpc('get_content_status')
  if (error) throw error
  return { data }
}

export const getAdminMe = async () => {
  const { data: { user }, error } = await supabase.auth.getUser()
  if (error) throw error
  return { data: { id: user.id, email: user.email, username: user.email } }
}

export const getAuditLogs = async (limit = 50, action = null) => {
  let query = supabase
    .from('audit_logs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (action) query = query.eq('action', action)
  const { data, error } = await query
  if (error) throw error
  return { data }
}
```

---

### `frontend/src/contexts/AuthContext.jsx` — REPLACE

```javascript
import { createContext, useContext, useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(undefined) // undefined = loading

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
    return () => subscription.unsubscribe()
  }, [])

  const logout = async () => {
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider value={{
      session,
      isAuthenticated: !!session,
      isLoading: session === undefined,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
```

---

## Summary: Changes by Category

| Category | Files Changed | Files Deleted | Files Added |
|---|---|---|---|
| Supabase client | — | `services/api.js` | `lib/supabase.js` |
| Services | `classes.js`, `subjects.js`, `papers.js`, `search.js`, `admin.js` | — | — |
| Auth | `contexts/AuthContext.jsx`, `pages/admin/LoginPage.jsx`, `components/admin/ProtectedRoute.jsx` | — | — |
| Pages | Minor: `DashboardPage.jsx` (stats call), `PapersPage.jsx` (upload), `BulkUploadTab.jsx` | — | — |
| Config | `vite.config.js` (remove proxy) | — | `.env.local` |
| Backend | — | Entire `backend/` dir | — |
| Docker | — | `Dockerfile`, `docker-compose.yml` | — |

**All page layouts, UI components, TailwindCSS classes, routing structure, and admin panel design remain completely unchanged.**
