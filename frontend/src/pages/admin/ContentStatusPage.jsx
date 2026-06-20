import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getContentStatus } from '../../services/admin'

export default function ContentStatusPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getContentStatus()
      .then(res => setData(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load content status'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return <div className="p-8 text-center text-red-500">{error}</div>
  }

  const examTypes = data?.exam_types || []
  const classes = data?.classes || []

  const shortLabel = (et) => {
    const map = {
      'Annual Exam': 'Annual',
      'Half Yearly Exam': 'Half Yearly',
      'Quarterly Exam': 'Quarterly',
      'Unit Test 1': 'UT 1',
      'Unit Test 2': 'UT 2',
      'Unit Test 3': 'UT 3',
    }
    return map[et] || et
  }

  const totalCells = classes.reduce((acc, cls) => acc + cls.subjects.length * examTypes.length, 0)
  const coveredCells = classes.reduce((acc, cls) =>
    acc + cls.subjects.reduce((a, sub) =>
      a + examTypes.filter(et => sub.coverage[et]).length, 0), 0)
  const pct = totalCells > 0 ? Math.round((coveredCells / totalCells) * 100) : 0

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Content Status</h1>
          <p className="text-gray-500 text-sm mt-1">See which question papers and answer keys are missing</p>
        </div>
        <Link to="/admin/papers" className="btn-primary text-sm">
          + Upload Paper
        </Link>
      </div>

      {/* Overall coverage bar */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-semibold text-gray-700">Overall Coverage</p>
          <p className="text-sm font-bold text-gray-900">{coveredCells} / {totalCells} slots filled ({pct}%)</p>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center gap-6 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-emerald-500 inline-block" /> Has content</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-red-200 inline-block" /> Missing</span>
        </div>
      </div>

      {/* Per-class tables */}
      <div className="space-y-8">
        {classes.map(cls => {
          const clsCovered = cls.subjects.reduce((a, sub) => a + examTypes.filter(et => sub.coverage[et]).length, 0)
          const clsTotal = cls.subjects.length * examTypes.length
          const clsPct = clsTotal > 0 ? Math.round((clsCovered / clsTotal) * 100) : 0

          return (
            <div key={cls.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-gray-50">
                <h2 className="font-bold text-gray-800 text-base">{cls.name}</h2>
                <span className={`text-xs font-bold px-3 py-1 rounded-full ${clsPct === 100 ? 'bg-emerald-100 text-emerald-700' : clsPct >= 50 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-600'}`}>
                  {clsPct}% complete
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap sticky left-0 bg-gray-50 z-10">Subject</th>
                      {examTypes.map(et => (
                        <th key={et} className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap min-w-[90px]">
                          {shortLabel(et)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {cls.subjects.map(sub => (
                      <tr key={sub.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3 font-medium text-gray-800 whitespace-nowrap sticky left-0 bg-white z-10">{sub.name}</td>
                        {examTypes.map(et => (
                          <td key={et} className="px-4 py-3 text-center">
                            {sub.coverage[et]
                              ? <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-100 text-emerald-600 text-base" title="Content exists">✓</span>
                              : <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-red-50 text-red-300 text-base" title="Missing">✗</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
