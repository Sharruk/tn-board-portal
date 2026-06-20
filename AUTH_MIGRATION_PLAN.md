# Authentication Migration Plan
## Custom JWT + admins table → Supabase Auth

---

## Current Auth Architecture

```
Browser                    FastAPI                   PostgreSQL
  │                           │                          │
  │  POST /api/v1/auth/login  │                          │
  │  {username, password}     │                          │
  ├──────────────────────────►│                          │
  │                           │  SELECT * FROM admins    │
  │                           │  WHERE username = ?      │
  │                           ├─────────────────────────►│
  │                           │◄─────────────────────────┤
  │                           │  verify bcrypt hash       │
  │                           │  (Werkzeug)              │
  │                           │                          │
  │  {access_token: "JWT..."}│                          │
  │◄──────────────────────────┤                          │
  │                           │                          │
  │  localStorage.setItem(    │                          │
  │    'adminToken', JWT)     │                          │
  │                           │                          │
  │  GET /api/v1/admin/*      │                          │
  │  Authorization: Bearer JWT│                          │
  ├──────────────────────────►│                          │
  │                           │  jwt.decode(token)       │
  │                           │  get_current_admin()     │
  │                           │  SELECT admin by username│
  │                           ├─────────────────────────►│
```

**Key characteristics:**
- Custom `admins` table with `username`, `email`, `password_hash`
- JWT signed with `JWT_SECRET_KEY` env var (HS256, 60-min expiry)
- IP-based rate limiting in-memory (lost on restart)
- Account lockout stored in `admins.locked_until` (durable)
- Login accepts either `username` or `email` in the username field

---

## Target Auth Architecture

```
Browser                    Supabase Auth
  │                           │
  │  supabase.auth             │
  │  .signInWithPassword(     │
  │    {email, password})     │
  ├──────────────────────────►│
  │                           │  Internal bcrypt verify
  │                           │  Built-in rate limiting
  │                           │  Built-in account lockout
  │                           │
  │  {session: {              │
  │    access_token: "JWT",   │
  │    refresh_token: "...",  │
  │    user: {id, email}      │
  │  }}                       │
  │◄──────────────────────────┤
  │                           │
  │  supabase.auth             │
  │  .onAuthStateChange()     │  Session auto-refreshed
  │  (auto session mgmt)      │  by Supabase client
  │                           │
  │  All Supabase queries     │
  │  automatically include    │
  │  Authorization header     │
  │  (RLS enforces access)    │
```

**Key characteristics:**
- No custom admin table — `auth.users` managed by Supabase
- Session stored in localStorage by Supabase client (automatic)
- Session auto-refresh — no manual token renewal needed
- Rate limiting and lockout built into Supabase Auth
- Login uses email only (not username)
- RLS policies enforce admin-only access at database level

---

## What Migrates / What Is Deleted

| Current Component | Migration Action |
|---|---|
| `admins` table | 🗑️ Drop after migration complete |
| `admins.username` | Username concept is dropped — admins use email |
| `admins.password_hash` | Replaced by Supabase Auth internal storage |
| `admins.email` | Create Supabase Auth user with same email |
| `admins.failed_login_count` | Handled internally by Supabase Auth |
| `admins.locked_until` | Handled internally by Supabase Auth |
| `admins.last_login_at` | Available from `auth.users.last_sign_in_at` |
| `JWT_SECRET_KEY` env var | No longer needed |
| `backend/app/services/auth.py` | Deleted with backend |
| `backend/app/services/rate_limit.py` | Deleted with backend |
| `backend/app/api/auth.py` | Deleted with backend |
| `AuthContext.jsx` JWT logic | Replaced with Supabase session management |
| `adminToken` localStorage key | Replaced by Supabase session (auto-managed) |

---

## Admin User Migration Steps

### Step 1 — Create admin in Supabase Auth

1. Open Supabase Dashboard → **Authentication → Users**
2. Click **Add user → Create new user**
3. Enter:
   - **Email:** the admin's email address
   - **Password:** a new strong password (≥12 characters)
   - Check **"Auto-confirm user"**
4. Click **Create User**

> The admin's previous username (e.g., `admin`) is not used in the new system. Email is the login identifier.

### Step 2 — Test login before dropping old table

Verify `supabase.auth.signInWithPassword({ email, password })` works in the browser before dropping the `admins` table.

### Step 3 — Drop the admins table

```sql
-- Only run after verifying Supabase Auth login works end-to-end
DROP TABLE IF EXISTS admins CASCADE;
```

---

## Frontend Auth Changes

### `frontend/src/lib/supabase.js` (new file)
```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### `frontend/src/contexts/AuthContext.jsx` (replace)
```javascript
// Before: stores JWT string in localStorage manually
const [token, setToken] = useState(() => localStorage.getItem('adminToken'))

// After: subscribes to Supabase session state (auto-managed)
const [session, setSession] = useState(null)

useEffect(() => {
  supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
  const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
    setSession(session)
  })
  return () => subscription.unsubscribe()
}, [])
```

### `frontend/src/pages/admin/LoginPage.jsx` (change one call)
```javascript
// Before:
const { data } = await adminLogin(username, password)
login(data.access_token)

// After:
const { data, error } = await supabase.auth.signInWithPassword({ email, password })
if (error) throw error
// Session is set automatically via onAuthStateChange
```

### `frontend/src/components/admin/ProtectedRoute.jsx` (change check)
```javascript
// Before:
const { isAuthenticated } = useAuth()
if (!isAuthenticated) return <Navigate to="/admin/login" />

// After:
const { session } = useAuth()
if (!session) return <Navigate to="/admin/login" />
```

---

## Security Equivalence

| Security Feature | Current (JWT) | Target (Supabase Auth) |
|---|---|---|
| Password hashing | bcrypt via Werkzeug | bcrypt (Supabase internal) |
| Token expiry | 60 minutes (configurable) | 1 hour access + auto-refresh |
| Rate limiting | In-memory, resets on restart | Built-in, durable |
| Account lockout | DB-stored `locked_until` | Built-in |
| Token rotation | Manual re-login required | Automatic via refresh token |
| Brute force protection | Custom IP rate limiter | Supabase Auth built-in |
| Secret management | `JWT_SECRET_KEY` env var | Managed by Supabase internally |

**Overall: Target architecture is more secure, not less.**
