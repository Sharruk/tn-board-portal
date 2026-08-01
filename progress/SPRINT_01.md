# Sprint 01 — Version 1 Paper Metadata Upgrade

> **Status:** COMPLETE  
> **Branch:** `dev`  
> **Migration:** `016_paper_metadata_upgrade.sql`  
> **Build:** ✅ 0 errors · 116 modules · 25s

---

## Goal

Upgrade the paper metadata model so that the TN Board Portal can accurately represent real Tamil Nadu school examinations — including which month they were held, which district they came from, and the correct exam type (`First Mid Term Test`).

---

## Summary of Changes

### Database (Migration 016)
- Added `month TEXT` column (nullable, CHECK constraint on valid month names)
- Added `district TEXT` column (nullable)
- Created indexes: `idx_papers_month`, `idx_papers_district`
- Dropped and recreated `search_papers()` RPC with extended RETURNS TABLE and new `p_month`, `p_district` parameters (DEFAULT NULL — backward compatible)
- ILIKE search body extended to cover `month` and `district` fields
- **Data migration:** Class 10 July 2026 papers (Tamil, English, Mathematics, Science, Social Science, Chennai) migrated from `'Model Exam'` → `'First Mid Term Test'`, month set to `'July'`, district set to `'Chennai'`

### Services
| File | Change |
|---|---|
| `services/papers.js` | Added `First Mid Term Test` to `EXAM_TYPES`; added `MONTHS` and `TN_DISTRICTS` exports |
| `services/admin.js` | `uploadPaper()` reads `month` and `district` from FormData |
| `services/search.js` | Added `'first mid term test'` to `EXAM_PATTERNS`; passes `p_month`/`p_district` to RPC; returns `month`/`district` in results |

### Admin UI
| File | Change |
|---|---|
| `admin/PapersPage.jsx` | Imports constants from `services/papers.js`; Month + District dropdowns in Upload and Edit modals; Month + District columns in admin table; `exportCSV()` includes both |
| `admin/BulkUploadTab.jsx` | Imports constants from `services/papers.js`; `'First Mid Term Test'` in `EXAM_ALIASES`; month extraction from filename; Month + District per-row dropdowns |

### Public UI
| File | Change |
|---|---|
| `components/PaperCard.jsx` | Month+year combined badge (e.g. `"July 2026"`); District badge (orange, conditional) |
| `pages/PaperDetailPage.jsx` | Meta grid conditionally includes District; Year label uses month+year when month is set |
| `pages/SubjectPage.jsx` | `EXAM_CATEGORY_GROUPS` now includes `First Mid Term Test` between Monthly Test and Unit Tests |
| `pages/SearchPage.jsx` | Exam Type, Month, District filter dropdowns; `PaperResult` shows month+year and district badge; `SUGGESTIONS` includes `'First Mid Term Test'`, `'Chennai'`, `'Coimbatore'` |

---

## Files Changed

```
supabase/migrations/016_paper_metadata_upgrade.sql  [NEW]
frontend/src/services/papers.js                     [MODIFIED]
frontend/src/services/admin.js                      [MODIFIED]
frontend/src/services/search.js                     [MODIFIED]
frontend/src/pages/admin/PapersPage.jsx             [MODIFIED]
frontend/src/pages/admin/BulkUploadTab.jsx          [MODIFIED]
frontend/src/components/PaperCard.jsx               [MODIFIED]
frontend/src/pages/PaperDetailPage.jsx              [MODIFIED]
frontend/src/pages/SubjectPage.jsx                  [MODIFIED]
frontend/src/pages/SearchPage.jsx                   [MODIFIED]
CHANGELOG.md                                        [MODIFIED]
ROADMAP.md                                          [MODIFIED]
progress/SPRINT_01.md                               [NEW]
.ai/CHANGE_HISTORY.md                               [MODIFIED]
```

---

## Build Result

```
✓ 116 modules transformed
dist/assets/index-DDru64fZ.css   40.91 kB │ gzip:   7.01 kB
dist/assets/index-DaZ8YNms.js  641.38 kB │ gzip: 165.79 kB
✓ built in 25.43s
```

Pre-existing chunk size warning (641 kB) — not introduced by this sprint.

---

## Deployment Checklist

- [ ] Apply `supabase/migrations/016_paper_metadata_upgrade.sql` in Supabase Dashboard → SQL Editor
- [ ] Verify `papers` table has `month` and `district` columns
- [ ] Verify `search_papers` function exists with the new 6-parameter signature
- [ ] Deploy frontend (push to `dev` → merge to `main` when ready)
- [ ] Smoke test: upload a paper with Month=July, District=Chennai, Exam Type=First Mid Term Test
- [ ] Verify existing Class 10 papers now show "First Mid Term Test" and "July 2026"

---

## Testing Checklist

- [ ] Admin: Upload paper with Month, District, First Mid Term Test
- [ ] Admin: Bulk upload — verify month auto-extracted from filename containing "july"
- [ ] Admin: Edit existing paper — month and district dropdowns work
- [ ] Public: PaperCard shows "July 2026" for papers with month set
- [ ] Public: PaperCard shows district badge in orange
- [ ] Public: PaperDetailPage — Year field shows "July 2026" when month is set
- [ ] Public: PaperDetailPage — District row appears when set
- [ ] Public: SubjectPage shows "First Mid Term Test" category card when papers exist
- [ ] Search: "July" query returns papers with month=July
- [ ] Search: "Chennai" query returns papers with district=Chennai
- [ ] Search: "First Mid Term Test" returns correct papers
- [ ] Search: Exam Type dropdown filters correctly
- [ ] Search: Month dropdown filters correctly
- [ ] Search: District dropdown filters correctly
- [ ] Download: Original filename preserved (no regression)
- [ ] Mobile: All new badges and dropdowns responsive

---

## Notes

- **Backward compatible:** All new columns are nullable. Existing papers display with year-only badge and no district badge — no visual regression.
- **No architecture changes:** React + Vite + Supabase + Vercel unchanged.
- **Single source of truth:** `EXAM_TYPES`, `MONTHS`, `TN_DISTRICTS` now exported from `services/papers.js` — not duplicated in admin pages.
