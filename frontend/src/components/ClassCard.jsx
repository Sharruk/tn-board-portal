import { Link } from 'react-router-dom'

const CLASS_COLORS = {
  9:  { bg: 'bg-blue-50',   ring: 'ring-blue-200',   text: 'text-blue-700',   btn: 'text-blue-600 group-hover:text-blue-800' },
  10: { bg: 'bg-violet-50', ring: 'ring-violet-200', text: 'text-violet-700', btn: 'text-violet-600 group-hover:text-violet-800' },
  11: { bg: 'bg-emerald-50',ring: 'ring-emerald-200',text: 'text-emerald-700',btn: 'text-emerald-600 group-hover:text-emerald-800' },
  12: { bg: 'bg-orange-50', ring: 'ring-orange-200', text: 'text-orange-700', btn: 'text-orange-600 group-hover:text-orange-800' },
}

export default function ClassCard({ cls }) {
  const colors = CLASS_COLORS[cls.id] || CLASS_COLORS[9]
  return (
    <Link
      to={`/class/${cls.id}`}
      className="group card p-6 flex flex-col items-center text-center hover:border-blue-200"
    >
      <div className={`w-16 h-16 ${colors.bg} ring-2 ${colors.ring} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-105 transition-transform`}>
        <span className={`text-2xl font-extrabold ${colors.text}`}>{cls.id}</span>
      </div>
      <h3 className="text-lg font-bold text-gray-800 mb-1">{cls.name}</h3>
      <p className="text-sm text-gray-500 mb-4">
        {cls.subject_count} {cls.subject_count === 1 ? 'subject' : 'subjects'}
      </p>
      <span className={`text-sm font-semibold ${colors.btn} flex items-center gap-1`}>
        View Papers
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </span>
    </Link>
  )
}
