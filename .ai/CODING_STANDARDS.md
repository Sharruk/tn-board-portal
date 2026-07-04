# CODING_STANDARDS.md — Coding Standards
# TN Board Portal

> These standards apply to every file in `frontend/src/`. No exceptions.

---

## Language & Tooling

- **JavaScript** (not TypeScript — do not migrate to TS unless explicitly requested)
- **React 18** with functional components and hooks only (no class components)
- **Vite 5** as the build tool
- **Tailwind CSS 3** for all styling
- **React Router DOM v6** for routing

---

## File Naming

| Type | Convention | Example |
|------|-----------|---------|
| React components | PascalCase | `PaperCard.jsx`, `AdminLayout.jsx` |
| Service files | camelCase | `papers.js`, `admin.js` |
| Utility files | camelCase | `download.js` |
| Context files | PascalCase with "Context" suffix | `AuthContext.jsx` |
| Hook files | camelCase with "use" prefix | `useFetch.js` |

---

## Component Structure

Every React component should follow this structure:

```jsx
// 1. Imports (React first, then external, then local)
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getPaperById } from '../services/papers';
import LoadingSpinner from '../components/LoadingSpinner';

// 2. Component function (default export)
export default function PaperDetailPage() {
  // 3. State declarations
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 4. Effects
  useEffect(() => {
    loadPaper();
  }, [id]);

  // 5. Handler functions
  async function loadPaper() {
    setLoading(true);
    const { data, error } = await getPaperById(id);
    if (error) {
      setError(error.message);
    } else {
      setPaper(data);
    }
    setLoading(false);
  }

  // 6. Render guards (loading, error, null states)
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!paper) return <ErrorMessage message="Paper not found." />;

  // 7. Main render
  return (
    <div className="...">
      {/* JSX */}
    </div>
  );
}
```

---

## Service File Structure

All Supabase calls must go through service files:

```js
// services/papers.js

import { supabase } from '../lib/supabase';

/**
 * Fetch all published papers for a given subject.
 * @param {number} subjectId
 * @returns {{ data: Array, error: object|null }}
 */
export async function getPublishedPapers(subjectId) {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .eq('subject_id', subjectId)
    .eq('status', 'published')
    .order('year', { ascending: false });

  return { data, error };
}
```

Rules for service files:
- All functions are **async**
- Always return `{ data, error }` (the Supabase pattern)
- Use JSDoc comments for all exported functions
- Never throw; let callers handle `error`

---

## Error Handling

Every async call must handle errors:

```jsx
// ✅ Correct
const { data, error } = await getPublishedPapers(subjectId);
if (error) {
  setError('Failed to load papers. Please try again.');
  return;
}

// ❌ Wrong — no error handling
const { data } = await getPublishedPapers(subjectId);
setPapers(data);
```

Always show a user-friendly message via `<ErrorMessage>` component. Never expose raw Supabase error messages to users.

---

## Loading States

Every async operation must have a loading state:

```jsx
const [loading, setLoading] = useState(true);

// Show LoadingSpinner while loading
if (loading) return <LoadingSpinner />;
```

Use the shared `<LoadingSpinner />` component. Do not create one-off spinners.

---

## Tailwind CSS Usage

- Use Tailwind utility classes exclusively — no inline styles, no external CSS files (except `index.css` for global resets)
- Follow existing color conventions in the project (inspect current pages)
- Use responsive variants: `sm:`, `md:`, `lg:`
- Dark mode not yet implemented — do not add `dark:` classes until migration 1.2 is planned

---

## Constants & Magic Values

Never hard-code magic strings. Extract repeated values:

```js
// ❌ Bad
if (paper.status === 'published') { ... }

// ✅ Better — or at minimum document the allowed values
const PAPER_STATUS = {
  DRAFT: 'draft',
  PUBLISHED: 'published',
  ARCHIVED: 'archived',
};
```

---

## No `console.log` in Production Code

Remove all `console.log`, `console.error`, `console.warn` from committed code.
Debugging logs must be removed before commits.

---

## Accessibility

- Every image must have an `alt` attribute
- Every form input must have an associated `<label>` (or `aria-label`)
- Interactive elements must be focusable (use `<button>` not `<div onClick>`)
- Use semantic HTML: `<nav>`, `<main>`, `<article>`, `<section>`, `<aside>`, `<header>`, `<footer>`

---

## Form Validation

Every admin form must validate before submitting:

```jsx
function handleSubmit(e) {
  e.preventDefault();
  
  // Validate
  if (!title.trim()) {
    setError('Title is required.');
    return;
  }
  
  // Submit
  await createNotice({ title, ... });
}
```

---

## React Router

- Use `<Link>` for internal navigation — never `<a href>` for app routes
- Use `useNavigate()` for programmatic navigation
- Use `useParams()` to read route params
- All admin routes are nested under `/admin/*` and wrapped in `ProtectedRoute`

---

## Performance Guidelines

- Use `useMemo` and `useCallback` only when there is a measurable performance issue — not preemptively
- Lazy-load heavy pages (planned in v1.1):
  ```jsx
  const SearchPage = lazy(() => import('./pages/SearchPage'));
  ```
- Never block the main thread with synchronous operations in render

---

## What Good Code Looks Like

Good code in this project is:
- **Readable** — another engineer can understand it without context
- **Consistent** — follows the same patterns as the rest of the codebase
- **Complete** — loading states, error states, empty states, all handled
- **Accessible** — semantic HTML, proper labels
- **Tested** — build passes, manually verified in browser
