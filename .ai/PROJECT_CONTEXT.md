# PROJECT_CONTEXT.md — Project Vision & Capabilities
# TN Board Portal

---

## 1. Problem Statement
Tamil Nadu State Board school students (Classes 9–12) frequently face difficulties accessing verified, high-quality past question papers, answer keys, official notices, and study resources.

**TN Board Portal** provides a free, fast, centralized platform for discovering, viewing, and downloading official curriculum question papers and answer keys with explanation videos and community resources.

---

## 2. Key Platform Capabilities

### Public Student Portal
- **Browse by Class & Subject**: Classes 9, 10, 11, and 12 with subject filtering.
- **Full-Text Search**: Fast search across paper titles, exam types, districts, and subjects.
- **Paper Detail Page**: Embedded PDF viewer, paper metadata, approved description, YouTube explanation video embed, and one-click downloads.
- **Direct Downloads**: Downloads delivered with clean, approved filenames (e.g. `Class10_Science_MonthlyTest_August2026_Chennai_QP.pdf`) via `Content-Disposition`.
- **Contributor Attribution**: Highlighting students/teachers who contributed material (`Contributed by: <Name>`) while protecting email privacy.

### Contributor Material Submission Flow
- Authenticated users can upload past papers and answer keys with notes and metadata.
- Files are saved to a private `submissions` storage bucket until reviewed by administrators.

### Admin Approval & Publishing Workflow
- Administrators review pending submissions in the Admin Portal.
- Review modal supports setting/editing:
  1. **Paper Title** (human-readable title for public display).
  2. **Download File Name** (clean file name for student downloads).
  3. **Description** (paper summary/notes rendered on detail page).
  4. **YouTube URL** (optional explanation video).
  5. **Academic Metadata** (Class, Subject, Exam Type, Year, Month, District).
- Approval copies files to the public `papers` bucket and creates published paper records.

---

## 3. Technology Stack Overview

- **Frontend**: React 18, Vite 5, Tailwind CSS, Lucide icons, hosted on Vercel.
- **Backend API**: FastAPI 0.115, Python 3.12, Uvicorn, deployed serverlessly on Vercel (`api/index.py`).
- **Database & Storage**: Supabase PostgreSQL with migrations `001`–`025` and Supabase Object Storage.
- **Authentication**: Firebase Authentication with Google Sign-In, token extraction, and FastAPI backend ID token verification.
- **Testing & Tooling**: pytest for backend test suite, Vite production build, Docker for local backend testing.
