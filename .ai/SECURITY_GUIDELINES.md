# SECURITY_GUIDELINES.md — Security & Authentication Standards
# TN Board Portal

---

## 1. Secrets & Environment Variables

1. **Zero Secret Exposure**:
   - Never commit `.env`, private keys, Firebase service account credentials, or Supabase service role keys to Git.
   - Verify `.gitignore` includes all local credentials and temporary artifacts.
2. **Environment Variable Naming**:
   - Frontend variables: `VITE_FIREBASE_*`, `VITE_SUPABASE_*`, `VITE_API_BASE_URL`.
   - Backend variables: `FIREBASE_SERVICE_ACCOUNT_JSON`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `ADMIN_EMAIL`.

---

## 2. Authentication & Authorization

1. **Firebase Authentication**:
   - Frontend authenticates users via Firebase Google Sign-In (`signInWithPopup`).
   - Frontend acquires the Firebase ID token (`getIdToken()`) and sends it in the `Authorization: Bearer <token>` header.
2. **FastAPI Token Verification**:
   - The backend verifies Firebase ID tokens using `google.oauth2.id_token.verify_firebase_token`.
   - Role-based access control (`require_admin`, `require_super_admin`) validates the decoded email and user database record before granting access to admin endpoints.
3. **Contributor Email Privacy**:
   - Never include submitter or contributor email addresses in public API schemas (`PaperResponse`, `PaperSummary`, `PaperSearchResult`) or public pages.

---

## 3. Storage & Database Protection

1. **Storage Access Separation**:
   - Private bucket `submissions`: Accessible only via backend service role or authorized admin proxy downloads.
   - Public bucket `papers`: Read-only public access for published question papers and answer keys.
2. **Row Level Security (RLS)**:
   - All Supabase PostgreSQL tables must enforce Row Level Security policies.
