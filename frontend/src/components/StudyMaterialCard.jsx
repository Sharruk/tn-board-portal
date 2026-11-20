import { Link } from 'react-router-dom'

export default function StudyMaterialCard({
  item,
  showSubject = true,
  showClass = true,
  showCategory = true,
}) {
  const fileCount = item.file_count ?? item.files?.length ?? 0
  const linkCount = item.external_links?.length ?? 0

  // Strictly correct pluralization: "1 file" vs "2 files", never "1 files"
  let resourceLabel = ''
  if (fileCount > 0) {
    resourceLabel = fileCount === 1 ? '1 file (PDF)' : `${fileCount} files`
  } else if (linkCount > 0) {
    resourceLabel = linkCount === 1 ? '1 video / link' : `${linkCount} links`
  } else {
    resourceLabel = 'Study material'
  }

  const mediumLabel =
    item.medium === 'tamil' ? 'தமிழ் வழி' :
    item.medium === 'english' ? 'English' :
    item.medium === 'both' ? 'Tamil & English' : null

  const materialUrl = `/study-materials/${item.slug}`

  return (
    <div className="card p-4 sm:p-5 flex flex-col justify-between gap-3 h-full hover:border-blue-200 transition-all">
      <div>
        {/* Top Header: Title + Category Pill */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <Link
            to={materialUrl}
            className="text-sm sm:text-base font-semibold text-gray-800 leading-snug line-clamp-2 hover:text-blue-600 transition-colors flex-1"
          >
            {item.title}
          </Link>
          {showCategory && item.category_name && (
            <span className="badge shrink-0 bg-blue-50 text-blue-700 border border-blue-100 text-[11px] font-bold">
              {item.category_icon && <span className="mr-1">{item.category_icon}</span>}
              {item.category_name}
            </span>
          )}
        </div>

        {/* Secondary Metadata Badges */}
        <div className="flex items-center gap-1.5 flex-wrap text-[11px]">
          {showClass && (
            <span className="badge bg-gray-100 text-gray-700 font-medium">
              {item.class_name || (item.class_id ? `Class ${item.class_id}` : null)}
            </span>
          )}
          {showSubject && item.subject_name && (
            <span className="badge bg-purple-50 text-purple-700 font-medium border border-purple-100">
              {item.subject_name}
            </span>
          )}
          {mediumLabel && (
            <span className="badge bg-amber-50 text-amber-800 font-medium border border-amber-100">
              {mediumLabel}
            </span>
          )}
          {item.contributor_name && (
            <span className="badge bg-amber-50 text-amber-800 font-medium border border-amber-200/70" title={`Contributed by ${item.contributor_name}`}>
              🏆 {item.contributor_name}
            </span>
          )}
          {(item.chapter_name || item.unit) && (
            <span className="badge bg-blue-50 text-blue-700 font-medium">
              {[item.unit, item.chapter_name].filter(Boolean).join(' • ')}
            </span>
          )}
        </div>

        {/* Description Snippet */}
        {item.description && (
          <p className="text-xs text-gray-500 mt-2 line-clamp-2 leading-relaxed">
            {item.description}
          </p>
        )}
      </div>

      {/* Telemetry info */}
      <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
        <span className="flex items-center gap-1">
          <span>⬇️</span>
          <span>{(item.download_count || 0).toLocaleString()} download{(item.download_count || 0) !== 1 ? 's' : ''}</span>
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <span>👁️</span>
          <span>{(item.view_count || 0).toLocaleString()} view{(item.view_count || 0) !== 1 ? 's' : ''}</span>
        </span>
      </div>

      {/* Bottom Action Bar */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-100">
        <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>{resourceLabel}</span>
        </div>

        <Link
          to={materialUrl}
          className="text-xs sm:text-sm text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 group"
        >
          <span>View Details</span>
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </div>
  )
}
