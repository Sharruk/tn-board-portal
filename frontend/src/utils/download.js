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
function _resolveFilename(filename, title, fallbackName) {
  return filename || (title ? `${title}.pdf` : fallbackName)
}

/**
 * Fetch a URL and return a Blob.  Throws on network/HTTP failure.
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
 *   1. `filename` (original_filename from DB)
 *   2. `title` + ".pdf"
 *   3. "download.pdf"
 *
 * @param {string}      url      - Supabase Storage public URL
 * @param {string|null} [title]  - Paper title (fallback)
 * @param {string|null} [filename] - Original uploaded filename (preferred)
 */
export async function downloadPaper(url, title, filename) {
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

    // Revoke after a short delay to allow the browser to start the download
    setTimeout(() => URL.revokeObjectURL(blobUrl), 10000)
  } catch {
    // Network error fallback — open directly (UUID may show, but better than nothing)
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

// =============================================================================
// viewPdf — open the PDF in a new browser tab
// =============================================================================
/**
 * Open a PDF in a new tab.
 *
 * @param {string} url - Supabase Storage public URL
 */
export function viewPdf(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
