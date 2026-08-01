import { Link } from 'react-router-dom'
import { NEWS_CATEGORY_ICONS, formatPublishedDate } from '../services/news'

// ── YouTube play icon ─────────────────────────────────────────────────────────

function YouTubeBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700"
      title="Video available"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
        <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
      </svg>
      Video
    </span>
  )
}

/**
 * NewsCard — used in the News listing page and the Home page.
 *
 * Props:
 *   article  — row from news_updates (with class_name resolved)
 *   compact  — if true, renders a slim single-row variant for the home page strip
 */
export default function NewsCard({ article, compact = false }) {
  const icon      = NEWS_CATEGORY_ICONS[article.category] ?? '📰'
  const published = formatPublishedDate(article.published_at || article.created_at, { short: true })

  if (compact) {
    // ── Compact variant — Home page "Latest Education News" strip ─────────────
    return (
      <Link
        to={`/news/${article.slug}`}
        className="flex items-center gap-3 p-3 rounded-xl hover:bg-blue-50 transition-colors group"
      >
        {/* Thumbnail or icon */}
        {article.thumbnail_url ? (
          <img
            src={article.thumbnail_url}
            alt={article.thumbnail_alt || article.title}
            className="w-12 h-12 rounded-lg object-cover shrink-0"
          />
        ) : (
          <span className="text-2xl shrink-0 w-12 h-12 flex items-center justify-center bg-blue-50 rounded-lg">
            {icon}
          </span>
        )}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate group-hover:text-blue-700 transition-colors">
            {article.title}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{article.category} · {published}</p>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {article.youtube_url && <YouTubeBadge />}
          {article.is_pinned && (
            <span className="text-xs font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
              📌 Pinned
            </span>
          )}
        </div>
      </Link>
    )
  }

  // ── Full card variant — News listing page ────────────────────────────────────
  return (
    <div className={`bg-white rounded-2xl border ${article.is_pinned ? 'border-amber-300 shadow-amber-100' : 'border-gray-100'} shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col group`}>
      {/* Pinned stripe */}
      {article.is_pinned && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-1.5 flex items-center gap-1.5">
          <span className="text-sm">📌</span>
          <span className="text-xs font-semibold text-amber-700">Pinned Article</span>
        </div>
      )}

      {/* Thumbnail */}
      <Link to={`/news/${article.slug}`} className="block overflow-hidden">
        {article.thumbnail_url ? (
          <img
            src={article.thumbnail_url}
            alt={article.thumbnail_alt || article.title}
            className="w-full h-44 object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-44 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
            <span className="text-5xl opacity-60">{icon}</span>
          </div>
        )}
      </Link>

      <div className="p-4 flex flex-col flex-1">
        {/* Badges */}
        <div className="flex flex-wrap items-center gap-1.5 mb-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
            {icon} {article.category}
          </span>
          {article.class_name && (
            <span className="badge bg-purple-50 text-purple-700 text-xs">{article.class_name}</span>
          )}
          {article.youtube_url && <YouTubeBadge />}
        </div>

        {/* Title */}
        <Link
          to={`/news/${article.slug}`}
          className="font-bold text-gray-900 text-sm leading-snug hover:text-blue-700 transition-colors line-clamp-2 mb-2"
        >
          {article.title}
        </Link>

        {/* Summary */}
        {article.summary && (
          <p className="text-xs text-gray-500 leading-relaxed line-clamp-2 mb-3 flex-1">
            {article.summary}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-50 mt-auto">
          <span className="text-xs text-gray-400">📅 {published}</span>
          <Link
            to={`/news/${article.slug}`}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
          >
            Read More →
          </Link>
        </div>
      </div>
    </div>
  )
}
