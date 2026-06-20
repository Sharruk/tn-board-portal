import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import ClassCard from '../components/ClassCard'
import PaperCard from '../components/PaperCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { getClasses } from '../services/classes'
import { getRecentPapers, getPopularPapers } from '../services/papers'

export default function HomePage() {
  const [classes, setClasses] = useState([])
  const [recentPapers, setRecentPapers] = useState([])
  const [popularPapers, setPopularPapers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getClasses(), getRecentPapers(10), getPopularPapers(10)])
      .then(([clsRes, recentRes, popularRes]) => {
        setClasses(clsRes.data)
        setRecentPapers(recentRes.data)
        setPopularPapers(popularRes.data)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-700 via-blue-800 to-blue-900 text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-block bg-blue-600 text-blue-100 text-xs font-semibold px-3 py-1 rounded-full mb-5 tracking-wide uppercase">
            Tamil Nadu State Board
          </span>
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4 leading-tight">
            Question Papers &amp;<br className="hidden md:block" /> Answer Keys
          </h1>
          <p className="text-blue-200 text-lg mb-10 max-w-xl mx-auto">
            Free study materials for Class 9, 10, 11 &amp; 12 — Unit Tests, Quarterly,
            Half Yearly, and Annual Exams.
          </p>
          <SearchBar size="lg" placeholder="Search by subject, exam type, or year…" />
          <p className="mt-4 text-blue-300 text-sm">Try: "Class 10 Maths Annual Exam" or "Physics Answer Key"</p>
        </div>
      </section>

      {/* Stats bar */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-5 grid grid-cols-3 divide-x divide-gray-100 text-center">
          {[
            { label: 'Classes', value: '4' },
            { label: 'Subjects', value: '32' },
            { label: 'Free Access', value: '100%' },
          ].map(s => (
            <div key={s.label} className="py-1">
              <p className="text-2xl font-extrabold text-blue-600">{s.value}</p>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Classes */}
      <section className="max-w-6xl mx-auto px-4 py-14">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Choose Your Class</h2>
            <p className="text-gray-500 text-sm mt-1">Select your class to browse subjects and exam papers</p>
          </div>
        </div>

        {loading ? (
          <LoadingSpinner text="Loading classes…" />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {classes.map(cls => <ClassCard key={cls.id} cls={cls} />)}
          </div>
        )}
      </section>

      {/* Recently Added Papers */}
      <section className="bg-white border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-4 py-14">
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Recently Added</h2>
              <p className="text-gray-500 text-sm mt-1">Latest question papers uploaded to the portal</p>
            </div>
            <Link to="/search" className="text-sm text-blue-600 hover:text-blue-800 font-medium hidden sm:block">
              Browse all →
            </Link>
          </div>

          {loading ? (
            <LoadingSpinner text="Loading papers…" />
          ) : recentPapers.length === 0 ? (
            <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
              <div className="text-5xl mb-4">📄</div>
              <p className="text-gray-500 font-medium">No papers uploaded yet.</p>
              <p className="text-gray-400 text-sm mt-1">Check back soon — papers will appear here after admin uploads.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentPapers.slice(0, 10).map(p => <PaperCard key={p.id} paper={p} showSubject />)}
            </div>
          )}
        </div>
      </section>

      {/* Most Downloaded Papers */}
      {!loading && popularPapers.length > 0 && (
        <section className="bg-gray-50 border-t border-gray-100">
          <div className="max-w-6xl mx-auto px-4 py-14">
            <div className="flex items-end justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Most Downloaded</h2>
                <p className="text-gray-500 text-sm mt-1">Top papers by number of downloads</p>
              </div>
              <Link to="/search" className="text-sm text-blue-600 hover:text-blue-800 font-medium hidden sm:block">
                Browse all →
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {popularPapers.slice(0, 10).map(p => <PaperCard key={p.id} paper={p} showSubject showDownloads />)}
            </div>
          </div>
        </section>
      )}

      {/* How it works */}
      <section className="max-w-5xl mx-auto px-4 py-14">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { step: '1', title: 'Select Your Class', desc: 'Choose from Class 9, 10, 11, or 12 to see all available subjects.', icon: '🎓' },
            { step: '2', title: 'Pick a Subject', desc: 'Browse subjects and select the exam type — Unit Test, Quarterly, Annual, and more.', icon: '📚' },
            { step: '3', title: 'Download Free', desc: 'Download question papers or answer keys as PDF instantly. No sign-up needed.', icon: '⬇️' },
          ].map(item => (
            <div key={item.step} className="text-center">
              <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">{item.icon}</div>
              <h3 className="font-bold text-gray-800 mb-2">{item.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
