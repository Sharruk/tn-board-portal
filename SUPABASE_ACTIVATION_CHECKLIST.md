# Supabase Activation Checklist
## TN State Board Learning Platform

**Project:** https://fcxvrsgcvmlowehpilvr.supabase.co  
**Time required:** 15–20 minutes  
**Skill level required:** Basic — just copy, paste, and click

---

## Before you begin

You will need:
- A browser logged into [supabase.com](https://supabase.com)
- The file `COPY_PASTE_SQL_ORDER.md` open in another tab or window

You will visit three sections of the Supabase dashboard:
1. **SQL Editor** — to set up the database
2. **Storage** — to create the file bucket
3. **Authentication** — to create the admin account

---

## PART 1 — Database Setup
### Open the SQL Editor

**Click this link:**  
https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/sql/new

You will see a white text area. This is where you paste and run SQL.

---

### STEP 1 of 6 — Create the tables

**Purpose:** Creates all 5 database tables the application uses.

**What gets created:**
- `classes` — stores Class 9, 10, 11, 12
- `subjects` — stores every subject per class
- `papers` — stores uploaded question papers and answer keys
- `audit_logs` — records every admin action
- `search_queries` — records every search students make

**Instructions:**
1. Open `COPY_PASTE_SQL_ORDER.md`
2. Copy everything under **BLOCK 1 of 6**
3. Paste it into the SQL Editor
4. Click the green **Run** button (or press `Ctrl+Enter`)
5. Wait for the message: `Success. No rows returned`

**Verify it worked — paste this and click Run:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**You must see exactly these 5 rows before continuing:**
```
audit_logs
classes
papers
search_queries
subjects
```

If you see fewer than 5 rows, do not continue. Re-paste Block 1 and run again.

---

### STEP 2 of 6 — Load the class and subject data

**Purpose:** Fills the tables with the 4 classes and 32 subjects that students will browse.

**What gets inserted:**
- Class 9 — 5 subjects (Tamil, English, Mathematics, Science, Social Science)
- Class 10 — 5 subjects (Tamil, English, Mathematics, Science, Social Science)
- Class 11 — 11 subjects (Tamil, English, Mathematics, Physics, Chemistry, Biology, Computer Science, Computer Applications, Accountancy, Commerce, Economics)
- Class 12 — 11 subjects (same as Class 11)

**Instructions:**
1. Click **New query** at the top of the SQL Editor to open a fresh tab
2. Copy everything under **BLOCK 2 of 6** from `COPY_PASTE_SQL_ORDER.md`
3. Paste it into the SQL Editor
4. Click **Run**
5. Wait for the message: `Success. No rows returned`

**Verify it worked — paste this and click Run:**
```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
```

**You must see:**
```
class_count | subject_count
          4 |            32
```

If either number is wrong, do not continue.

---

### STEP 3 of 6 — Set access rules (security policies)

**Purpose:** Decides who can read or write each table.

**Rules this step creates:**
- Students (not logged in) can read classes, subjects, and visible papers. They cannot see hidden papers or admin data.
- Admins (logged in) can read and write everything.
- Students can log their searches but cannot read other students' searches.
- Audit logs are write-once — no one can delete or edit them.

**Instructions:**
1. Click **New query**
2. Copy everything under **BLOCK 3 of 6** from `COPY_PASTE_SQL_ORDER.md`
3. Paste and click **Run**

**Verify it worked — paste this and click Run:**
```sql
SELECT COUNT(*) AS policy_count
FROM pg_policies
WHERE schemaname = 'public';
```

**You must see:**
```
policy_count
          13
```

---

### STEP 4 of 6 — Create database functions

**Purpose:** Creates 4 special operations that the app calls directly from the browser.

**What gets created:**
- `increment_download_count` — safely adds 1 to the download counter when a student downloads a paper
- `get_admin_stats` — returns all dashboard numbers in one call (total papers, downloads, subjects, classes)
- `get_search_analytics` — returns the most popular and most recent search terms for the admin dashboard
- `get_content_status` — returns a grid showing which exam types have been uploaded for each subject

**Instructions:**
1. Click **New query**
2. Copy everything under **BLOCK 4 of 6** from `COPY_PASTE_SQL_ORDER.md`
3. Paste and click **Run**

**Verify it worked — paste this and click Run:**
```sql
SELECT * FROM get_admin_stats();
```

**You must see 1 row with these values:**
```
total_papers | total_downloads | total_subjects | total_classes | visible_papers | question_papers | answer_keys
           0 |               0 |             32 |             4 |              0 |               0 |           0
```

`total_subjects = 32` and `total_classes = 4` confirms the data and functions are both working.

---

### STEP 5 of 6 — Create analytics objects

**Purpose:** Adds a speed optimisation for search analytics and a cleanup tool to prevent the search history table from growing too large over time.

**What gets created:**
- A database index that makes search analytics load faster
- A view called `search_term_counts` — a ready-made summary of the most common search terms
- A function `prune_old_search_queries` — a cleanup tool you can run manually to delete old search history

**Instructions:**
1. Click **New query**
2. Copy everything under **BLOCK 5 of 6** from `COPY_PASTE_SQL_ORDER.md`
3. Paste and click **Run**

**Verify it worked — paste this and click Run:**
```sql
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public';
```

**You must see:**
```
search_term_counts
```

---

### STEP 6 of 6 — Create the search function

**Purpose:** Creates the function that powers the search bar. It searches across paper titles, exam types, subject names, and class names all at once.

**What gets created:**
- `search_papers` — the cross-table search function used by the search page

**Instructions:**
1. Click **New query**
2. Copy everything under **BLOCK 6 of 6** from `COPY_PASTE_SQL_ORDER.md`
3. Paste and click **Run**

**Verify it worked — paste this and click Run:**
```sql
SELECT * FROM search_papers('maths', NULL, NULL, NULL);
```

**You must see:**  
0 rows returned, and **no error message**. Zero results is correct because no papers have been uploaded yet. If you see an error instead of empty results, the function did not install correctly.

---

### Final database verification — run this complete check

Paste the entire block below into a new query and click **Run**. All 7 checks must pass.

```sql
-- Check 1: All 5 tables
SELECT 'TABLES' AS check_name,
       COUNT(*) AS count,
       CASE WHEN COUNT(*) = 5 THEN 'PASS' ELSE 'FAIL' END AS result
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE';

-- Check 2: All 6 functions
SELECT 'FUNCTIONS' AS check_name,
       COUNT(*) AS count,
       CASE WHEN COUNT(*) = 6 THEN 'PASS' ELSE 'FAIL' END AS result
FROM information_schema.routines
WHERE routine_schema = 'public';

-- Check 3: 13 security policies
SELECT 'POLICIES' AS check_name,
       COUNT(*) AS count,
       CASE WHEN COUNT(*) = 13 THEN 'PASS' ELSE 'FAIL' END AS result
FROM pg_policies
WHERE schemaname = 'public';

-- Check 4: 1 view
SELECT 'VIEWS' AS check_name,
       COUNT(*) AS count,
       CASE WHEN COUNT(*) = 1 THEN 'PASS' ELSE 'FAIL' END AS result
FROM information_schema.views
WHERE table_schema = 'public';

-- Check 5: Seed data
SELECT 'SEED DATA' AS check_name,
       (SELECT COUNT(*) FROM classes)::TEXT || ' classes / ' ||
       (SELECT COUNT(*) FROM subjects)::TEXT || ' subjects' AS count,
       CASE WHEN (SELECT COUNT(*) FROM classes) = 4
             AND (SELECT COUNT(*) FROM subjects) = 32
            THEN 'PASS' ELSE 'FAIL' END AS result;
```

**All 5 rows must show `PASS` in the result column.** If any show `FAIL`, re-run the corresponding block.

---

## PART 2 — File Storage Setup

### STEP 7 — Create the file bucket

**Purpose:** Creates the storage location where uploaded PDF files will be saved.

**Click this link to open Storage:**  
https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/storage/buckets

**Instructions:**

1. Click the **New bucket** button
2. Fill in the form exactly as follows:

   | Field | Value to enter |
   |---|---|
   | **Name** | `papers` |
   | **Public bucket** | Toggle this **ON** (the toggle turns green) |
   | **File size limit** | `52428800` |
   | **Allowed MIME types** | `application/pdf` |

3. Click **Create bucket**

**You should see** the bucket named `papers` appear in the list with a globe icon (indicating it is public).

> **Why public?** Students need to view and download PDFs without logging in. The bucket is public for reading, but only the admin can upload or delete files (controlled by the security rules in the next step).

---

### STEP 8 — Add storage security rules

**Purpose:** Allows students to download PDFs but restricts uploading and deleting to the admin only.

**Instructions:**
1. Go back to the SQL Editor:  
   https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/sql/new
2. Click **New query**
3. Copy everything under **BLOCK 7** from `COPY_PASTE_SQL_ORDER.md`
4. Paste and click **Run**

**Verify it worked:**  
Go to Storage → select the `papers` bucket → click **Policies**.  
You should see 3 policies listed:
- `papers_bucket_public_read`
- `papers_bucket_admin_insert`
- `papers_bucket_admin_delete`

---

## PART 3 — Admin Account Setup

### STEP 9 — Create the admin user

**Purpose:** Creates the login account used to access the admin dashboard at `/admin/login`.

**Click this link to open Authentication:**  
https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/auth/users

**Instructions:**

1. Click **Add user** → then click **Create new user**
2. Fill in the form exactly as follows:

   | Field | What to enter |
   |---|---|
   | **Email** | Your admin email address (e.g. `admin@yourdomain.com`) |
   | **Password** | A strong password — at least 12 characters, mix of letters, numbers, and symbols |
   | **Auto Confirm User** | **Check this box** ✅ |

3. Click **Create User**

> **Why "Auto Confirm User" matters:** Without checking this box, Supabase sends a confirmation email. Until the link in that email is clicked, the account cannot log in. Checking this box skips the email step and activates the account immediately.

**Verify it worked:**  
The user appears in the list with status **Confirmed** (not "Waiting for verification").

---

### Email confirmation settings (one-time check)

To ensure future password resets work correctly, verify the email settings:

1. Go to: https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/auth/url-configuration
2. Under **Site URL**, confirm the value matches your app's URL
3. If the app is running locally: `http://localhost:5000`
4. If the app is deployed: your production URL

---

## PART 4 — Full Application Verification

After completing all steps above, verify the application works end-to-end.

### Public features

Open the app in a browser and check each item:

| What to do | What you should see |
|---|---|
| Open the homepage `/` | Four cards appear: Class 9, Class 10, Class 11, Class 12 |
| Click "Class 10" | A list of subjects appears |
| Click any subject | A message saying "No papers yet" (correct — none uploaded) |
| Type "maths" in the search bar | Search runs with 0 results and no error |
| Go to `/admin/login` | A login form appears |

### Admin features

| What to do | What you should see |
|---|---|
| Log in with your admin email and password | Redirected to the admin dashboard |
| Dashboard → Stats section | Shows 4 classes, 32 subjects, 0 papers |
| Dashboard → Content Status | A grid of all subjects with green/red indicators |
| Papers → Upload | An upload form appears |
| Papers → Bulk Upload | A bulk upload interface appears |

### After uploading a test paper

| What to do | What you should see |
|---|---|
| Upload a PDF to any class and subject | The paper appears in the Papers list |
| Go to the homepage | The paper appears in "Recently Added" |
| Click the paper | A download counter increments |
| Search for the subject name | The paper appears in search results |

---

## Summary — What each step does

| Step | What it does | Without it |
|---|---|---|
| 1 — Schema | Creates the 5 database tables | Nothing works — no structure to store data |
| 2 — Seed data | Fills in the 4 classes and 32 subjects | Homepage shows no class cards |
| 3 — RLS policies | Controls who can read and write what | All data is either blocked or exposed to everyone |
| 4 — Functions | Creates the 4 RPC operations | Downloads not counted; dashboard stats fail |
| 5 — Analytics | Speeds up search history; adds cleanup tool | Search analytics load slowly; table grows unbounded |
| 6 — Search function | Powers the search bar | Search page returns errors |
| 7 — Storage bucket | Creates the PDF file store | File uploads fail |
| 8 — Storage policies | Controls who can upload/download | Downloads blocked or uploads open to anyone |
| 9 — Admin user | Creates the login account | Admin dashboard inaccessible |
