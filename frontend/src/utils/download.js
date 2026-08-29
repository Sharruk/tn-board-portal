// =============================================================================
// PDF Utilities — download.js
// =============================================================================
// Why blob-fetch for both view AND download?
// ──────────────────────────────────────────
// Supabase Storage URLs are cross-origin CDN URLs.
//
// For DOWNLOAD: browsers ignore the `download` attribute on cross-origin
//   anchors, so the file saves with the UUID storage key instead of the
//   original filename.  A blob: URL is same-origin, so `download` is honoured.
//
// For VIEW: Chrome's PDF viewer titles the tab using the URL path — which
//   exposes the UUID storage key.  Opening a blob: URL instead shows the
//   filename we choose (or a neutral "blob:" label), hiding the UUID entirely.
//
// Both functions share the same fetch-to-blob core (_fetchBlob).
// =============================================================================

/**
 * Shared filename resolver.
 * Fallback chain: original_filename → title + ".pdf" → fallbackName
 *
 * @param {string|null} filename - original_filename from DB
 * @param {string|null} title    - paper title
 * @param {string}      fallbackName
 * @returns {string}
 */
function _isUuidOrPath(str) {
  if (!str || typeof str !== 'string') return true
  const trimmed = str.trim()
  // Matches UUID strings like 4b750e1e-c692-4c8c-b5bb-a7b8db31ed43 with or without extension
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(\.[a-z0-9]+)?$/i.test(trimmed)) {
    return true
  }
  // Matches Supabase storage URLs or object paths
  if (trimmed.includes('/storage/v1/object/') || trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return true
  }
  return false
}

/**
 * Shared filename resolver.
 * Fallback chain: original_filename (if not UUID) → title + ".pdf" → fallbackName
 *
 * @param {string|null} filename - original_filename from DB
 * @param {string|null} title    - paper title
 * @param {string}      fallbackName
 * @returns {string}
 */
export function _resolveFilename(filename, title, fallbackName = 'download.pdf') {
  if (filename && !_isUuidOrPath(filename)) {
    const clean = filename.trim()
    return clean.toLowerCase().endsWith('.pdf') ? clean : `${clean}.pdf`
  }
  if (title && !_isUuidOrPath(title)) {
    const clean = title.replace(/[/\\?%*:|"<>]/g, '_').trim()
    if (clean) {
      return clean.toLowerCase().endsWith('.pdf') ? clean : `${clean}.pdf`
    }
  }
  return fallbackName
}

/**
 * Fetch a URL and return a Blob. Throws on network/HTTP failure.
 *
 * @param {string} url
 * @returns {Promise<Blob>}
 */
async function _fetchBlob(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.blob()
}

// =============================================================================
// downloadPaper — save the PDF to disk with the correct filename
// =============================================================================
/**
 * Download a paper PDF with the correct original filename.
 *
 * Fallback order for the saved filename:
 *   1. `filename` (original_filename from DB, if not a UUID)
 *   2. `title` + ".pdf"
 *   3. "download.pdf"
 *
 * @param {string}      url      - Supabase Storage public URL
 * @param {string|null} [title]  - Paper title (fallback)
 * @param {string|null} [filename] - Original uploaded filename (preferred)
 */
export async function downloadPaper(url, title, filename) {
  if (!url) return
  const safeFilename = _resolveFilename(filename, title, 'download.pdf')

  try {
    const blob    = await _fetchBlob(url)
    const blobUrl = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href     = blobUrl
    a.download = safeFilename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

    // Revoke after a delay to allow the browser to start the download
    setTimeout(() => URL.revokeObjectURL(blobUrl), 15000)
  } catch {
    // Network error fallback — open directly
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

// =============================================================================
// viewPdf — open the PDF in a new browser tab via a blob URL
// =============================================================================
/**
 * Open a PDF in a new tab via blob URL to hide raw storage URLs.
 *
 * @param {string} url - Supabase Storage public or signed URL
 * @param {string|null} [title] - Paper title
 * @param {string|null} [filename] - Original filename
 */
export async function viewPdf(url, title, filename) {
  if (!url) return
  const safeFilename = _resolveFilename(filename, title, 'paper.pdf')

  try {
    const blob = await _fetchBlob(url)
    const pdfBlob = blob.type === 'application/pdf' ? blob : new Blob([blob], { type: 'application/pdf' })
    const blobUrl = URL.createObjectURL(pdfBlob)
    const newTab = window.open(blobUrl, '_blank', 'noopener,noreferrer')
    if (newTab) {
      try {
        newTab.document.title = safeFilename
      } catch {
        // Cross-window title change may be ignored in some browsers
      }
    } else {
      window.location.href = blobUrl
    }
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}
