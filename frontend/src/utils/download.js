/**
 * Download a paper PDF with the correct original filename.
 *
 * Why blob-fetch instead of a plain `<a download>` link?
 * ──────────────────────────────────────────────────────
 * The files are served from Supabase Storage (a cross-origin CDN URL).
 * Modern browsers silently ignore the `download` attribute on cross-origin
 * anchors — they open the file in a new tab instead of saving it, or they
 * save it using the server-side filename (the UUID storage key).
 *
 * By fetching the file as a Blob first, we obtain a same-origin
 * `blob:` URL.  An anchor pointing at a `blob:` URL always respects the
 * `download` attribute, so we can force any filename we want.
 *
 * Fallback order for the download filename:
 *   1. `filename` argument (original_filename from DB)
 *   2. `title` argument + ".pdf"
 *   3. "download.pdf"
 *
 * @param {string} url       - Public URL of the PDF in Supabase Storage
 * @param {string} [title]   - Paper title used as fallback filename
 * @param {string} [filename] - Original uploaded filename (preferred)
 */
export async function downloadPaper(url, title, filename) {
  // Determine the best filename — never expose the UUID storage path.
  const safeFilename =
    filename ||
    (title ? `${title}.pdf` : 'download.pdf')

  try {
    const res  = await fetch(url)
    const blob = await res.blob()
    const blobUrl = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href     = blobUrl
    a.download = safeFilename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

    // Revoke after a short delay to allow the download to start
    setTimeout(() => URL.revokeObjectURL(blobUrl), 10000)
  } catch {
    // If fetch fails (e.g. network error), open in a new tab as last resort.
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

