import { Link } from 'react-router-dom'
import { downloadPaper } from '../utils/download'

export default function PaperCard({ paper, showSubject = false, showDownloads = false }) {
  const isQuestion = paper.paper_type === 'question'
  const paperUrl = paper.slug ? `/paper/${paper.slug}` : `/paper/${paper.id}`

  return (
    <div className="card p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-800 leading-snug line-clamp-2 flex-1">
          {paper.title}
        </h3>
        <span className={`badge shrink-0 ${isQuestion ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
          {isQuestion ? 'Q Paper' : 'Answer Key'}
        </span>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="badge bg-gray-100 text-gray-600">{paper.exam_type}</span>
        <span className="badge bg-gray-100 text-gray-600">{paper.year}</span>
        {showSubject && paper.subject && (
          <span className="badge bg-purple-100 text-purple-700">{paper.subject.name}</span>
        )}
      </div>

      {showDownloads && paper.download_count > 0 && (
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
          </svg>
          {paper.download_count.toLocaleString()} download{paper.download_count !== 1 ? 's' : ''}
        </div>
      )}

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-50">
        <Link to={paperUrl} className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
          View Details
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
        {paper.public_url && (
          <button
            onClick={() => downloadPaper(paper.public_url, paper.title, paper.original_filename)}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
            </svg>
            Download
          </button>
        )}
      </div>
    </div>
  )
}
