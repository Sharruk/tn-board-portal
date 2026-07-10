import { Link } from 'react-router-dom'
import { CATEGORY_ICONS, isNoticeExpired } from '../services/notices'

/**
 * NoticeCard — compact card for the Official Notices listing and home page.
 *
 * Props:
 *   notice    — notice row from the DB (with class_name resolved)
 *   compact   — if true, renders a smaller single-row variant for the home page
 *
 * Visual states:
 *   Active notice   — white card, normal styling
 *   Archived notice — gray card (bg-gray-50, gray border), "Archive" badge,
 *                     expiry date shown. All links and navigation remain available.
 *                     Opacity is NOT reduced per design spec.
 */
export default function NoticeCard({ notice, compact = false }) {
  const icon       = CATEGORY_ICONS[notice.category] ?? '📄'
  const isArchived = isNoticeExpired(notice)

  const published = notice.created_at
    ? new Date(notice.created_at).toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : ''

  const expiresOn = notice.expires_at
    ? new Date(notice.expires_at).toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
      })
    : null

  if (compact) {
    // ── Compact variant — used on the Home page latest-notices strip ─────────
    return (
      <Link
        to={`/notice/${notice.id}`}
        className="flex items-center gap-3 p-3 rounded-xl hover:bg-blue-50 transition-colors group"
      >
        <span className="text-2xl shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate group-hover:text-blue-700 transition-colors">
            {notice.title}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{notice.category} · {notice.year}</p>
        </div>
        {notice.youtube_url && (
          <span
            className="inline-flex items-center gap-0.5 text-xs font-semibold bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full shrink-0"
            title="Has explanation video"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
              <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
            </svg>
            Video
          </span>
        )}
        {notice.is_pinned && (
          <span className="text-xs font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full shrink-0">
            📌 Pinned
          </span>
        )}
      </Link>
    )
  }

  // ── Full card variant — used on the Official Notices page ──────────────────
  //
  // Active notices:  white bg, normal border, blue icon bg
  // Archived notices: gray bg, gray border, gray icon bg, Archive badge, expiry date

  const cardBg      = isArchived ? 'bg-gray-50'  : 'bg-white'
  const cardBorder  = isArchived
    ? 'border-gray-200'
    : notice.is_pinned ? 'border-amber-300 shadow-amber-100' : 'border-gray-100'
  const iconBg      = isArchived ? 'bg-gray-100' : 'bg-blue-50'
  const titleColor  = isArchived ? 'text-gray-600 hover:text-gray-800' : 'text-gray-900 hover:text-blue-700'

  return (
    <div className={`${cardBg} rounded-2xl border ${cardBorder} shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col`}>

      {/* Pinned stripe — shown even for archived pinned notices */}
      {notice.is_pinned && (
        <div className={`${isArchived ? 'bg-gray-100 border-b border-gray-200' : 'bg-amber-50 border-b border-amber-200'} px-4 py-1.5 flex items-center gap-1.5`}>
          <span className="text-sm">📌</span>
          <span className={`text-xs font-semibold ${isArchived ? 'text-gray-500' : 'text-amber-700'}`}>
            {isArchived ? 'Pinned (Archived)' : 'Pinned Notice'}
          </span>
        </div>
      )}

      {/* Archive banner — replaces the pinned stripe position when not pinned */}
      {isArchived && !notice.is_pinned && (
        <div className="bg-gray-100 border-b border-gray-200 px-4 py-1.5 flex items-center gap-1.5">
          <span className="text-sm">🗂️</span>
          <span className="text-xs font-semibold text-gray-500">Archived Notice</span>
        </div>
      )}

      <div className="p-5 flex flex-col flex-1">
        {/* Icon + Title */}
        <div className="flex items-start gap-3 mb-3">
          <div className={`w-11 h-11 ${iconBg} rounded-xl flex items-center justify-center text-2xl shrink-0`}>
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <Link
              to={`/notice/${notice.id}`}
              className={`font-bold ${titleColor} text-sm leading-snug transition-colors line-clamp-2`}
            >
              {notice.title}
            </Link>
          </div>
        </div>

        {/* Meta badges */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${isArchived ? 'bg-gray-100 text-gray-600' : 'bg-blue-50 text-blue-700'}`}>
            {notice.category}
          </span>
          {notice.class_name && (
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${isArchived ? 'bg-gray-100 text-gray-500' : 'bg-purple-50 text-purple-700'}`}>
              {notice.class_name}
            </span>
          )}
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            {notice.year}
          </span>
          {notice.youtube_url && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700"
              title="Explanation video available"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
                <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
              </svg>
              Video
            </span>
          )}
          {/* Archive badge — replaces the old inline "Expired" badge */}
          {isArchived && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-200 text-gray-600 border border-gray-300">
              🗂️ Archive
            </span>
          )}
        </div>

        {/* Description snippet */}
        {notice.description && (
          <p className={`text-xs ${isArchived ? 'text-gray-400' : 'text-gray-500'} leading-relaxed line-clamp-2 mb-3 flex-1`}>
            {notice.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-auto">
          <div className={`flex flex-col gap-0.5 text-xs ${isArchived ? 'text-gray-400' : 'text-gray-400'}`}>
            <span>📅 {published}</span>
            {/* Show expiry date on archived cards */}
            {isArchived && expiresOn && (
              <span className="text-gray-400">Expired on: {expiresOn}</span>
            )}
            {notice.download_count > 0 && (
              <span>⬇ {notice.download_count.toLocaleString()}</span>
            )}
          </div>
          <Link
            to={`/notice/${notice.id}`}
            className={`text-xs font-semibold ${isArchived ? 'text-gray-500 hover:text-gray-700' : 'text-blue-600 hover:text-blue-800'} transition-colors`}
          >
            View →
          </Link>
        </div>
      </div>
    </div>
  )
}
