# Storage Migration Plan
## FastAPI Local/Supabase → Direct Supabase Storage from React

---

## Current Storage Architecture

The backend has a pluggable storage system with three providers:

| Provider | When Used | Status |
|---|---|---|
| `local` | Development (default) | Files saved to `/uploads/` on server filesystem — ephemeral |
| `supabase` | Production (if configured) | Files uploaded to Supabase Storage bucket `papers` |
| `s3` | Not implemented | Stub only — `NotImplementedError` |

In the current architecture, the **browser never talks to Supabase Storage directly.** All uploads go through FastAPI → FastAPI calls Supabase Storage → returns CDN URL to browser.

---

## Target Storage Architecture

The browser calls Supabase Storage **directly** using the `@supabase/supabase-js` SDK. FastAPI is eliminated from the upload path entirely.

```
Current:
  Browser → POST /api/v1/admin/papers (multipart) → FastAPI → Supabase Storage → DB insert

Target:
  Browser → Supabase Storage SDK → upload() → get public URL → Supabase DB insert()
```

---

## Bucket Review

### Existing bucket: `papers`

| Setting | Current | Required Change? |
|---|---|---|
| Name | `papers` | No change |
| Visibility | Public | No change — students need direct CDN access |
| File size limit | 50 MB | No change |
| Allowed MIME types | `application/pdf` | No change |

**No bucket changes required.**

---

## Storage RLS Policies Required

The storage policies defined in `supabase/README.md` must be in place:

```sql
-- Public can download (already in place if README was followed)
CREATE POLICY "papers_bucket_public_read"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'papers');

-- Admin can upload
CREATE POLICY "papers_bucket_admin_insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'papers' AND auth.uid() IS NOT NULL);

-- Admin can delete
CREATE POLICY "papers_bucket_admin_delete"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

---

## Upload Flow Comparison

### Current (FastAPI)
```python
# backend/app/api/admin.py
file_path, public_url = await save_file_locally(file)  # calls storage.py

# backend/app/services/storage.py — SupabaseStorageProvider.save()
stored_filename = f"{uuid.uuid4().hex}.{ext}"
client.storage.from_(bucket).upload(path=stored_filename, file=content, ...)
public_url = client.storage.from_(bucket).get_public_url(stored_filename)
return stored_filename, public_url
```

### Target (React + Supabase JS)
```javascript
// In PapersPage.jsx / BulkUploadTab.jsx
import { supabase } from '../../lib/supabase'

const ext = file.name.split('.').pop().toLowerCase()
const storedFilename = `${crypto.randomUUID()}.${ext}`

const { error: uploadError } = await supabase.storage
  .from('papers')
  .upload(storedFilename, file, {
    contentType: 'application/pdf',
    upsert: false,
  })
if (uploadError) throw uploadError

const { data: { publicUrl } } = supabase.storage
  .from('papers')
  .getPublicUrl(storedFilename)

// Then insert DB row
await supabase.from('papers').insert({
  subject_id, exam_type, year, title, paper_type, youtube_url,
  file_path: storedFilename,   // storage object key for future deletion
  public_url: publicUrl,
  is_visible: true,
})
```

---

## Delete Flow Comparison

### Current (FastAPI)
```python
# backend/app/api/admin.py
db.delete(paper)
db.commit()
if paper.file_path:
    delete_file_locally(paper.file_path)  # calls storage.py

# backend/app/services/storage.py — SupabaseStorageProvider.delete()
client.storage.from_(bucket).remove([stored_filename])
```

### Target (React + Supabase JS)
```javascript
// Get file_path from the paper record before deleting
const { data: paper } = await supabase.from('papers').select('file_path').eq('id', id).single()

// Delete storage file first
if (paper.file_path) {
  await supabase.storage.from('papers').remove([paper.file_path])
}

// Delete DB row
await supabase.from('papers').delete().eq('id', id)
```

---

## File URL Structure

No changes to URL structure. All existing `public_url` values in the database remain valid:

```
https://<project-id>.supabase.co/storage/v1/object/public/papers/<uuid>.pdf
```

Students bookmarking or sharing PDF links will not be affected.

---

## Validation Rules (moved to frontend)

Current FastAPI validation (in `storage.py`):
- PDF only: `ext not in {'pdf'}` → reject
- Max 50 MB: `len(content) > MAX_FILE_SIZE_MB * 1024 * 1024` → reject

Target frontend validation (before upload):
```javascript
const ALLOWED_TYPES = ['application/pdf']
const MAX_SIZE_MB = 50

function validateFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error('Only PDF files are supported.')
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    throw new Error(`File too large. Maximum size is ${MAX_SIZE_MB} MB.`)
  }
}
```

> Note: Supabase bucket settings (MIME type + size limit) also enforce these server-side — double validation.

---

## Existing Locally-Stored Files

If any papers were uploaded with `STORAGE_BACKEND=local` (dev mode), their `public_url` values are `/uploads/<uuid>.pdf` — these are relative URLs pointing to the FastAPI server, which will no longer exist.

**Action required for any locally-stored papers:**
1. Identify: `SELECT id, title, public_url FROM papers WHERE public_url LIKE '/uploads/%'`
2. Re-upload those PDFs through the new admin UI (Supabase Storage)
3. Or upload manually to Supabase Storage and update the DB rows directly

Papers already on Supabase Storage (public_url starts with `https://...supabase.co`) need no action.

---

## Summary

| Aspect | Change Required |
|---|---|
| Supabase bucket name | None |
| Bucket visibility | None |
| Storage RLS policies | Verify/apply from supabase/README.md |
| Upload logic | Moved from FastAPI to React (frontend) |
| Delete logic | Moved from FastAPI to React (frontend) |
| File validation | Moved to frontend + enforced by bucket settings |
| Existing Supabase CDN URLs | No change — all continue working |
| Existing local-storage URLs | Must re-upload through new admin UI |
