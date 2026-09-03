import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import ClassCard from '../components/ClassCard'
import PaperCard from '../components/PaperCard'
import NoticeCard from '../components/NoticeCard'
import NewsCard from '../components/NewsCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { getClasses } from '../services/classes'
import { getRecentPapers, getPopularPapers } from '../services/papers'
import { getRecentNotices, CATEGORY_ICONS } from '../services/notices'
import { getRecentNews } from '../services/news'
import { getLeaderboard } from '../services/leaderboard'

export default function HomePage() {
  const [classes, setClasses] = useState([])
  const [recentPapers, setRecentPapers] = useState([])
  const [popularPapers, setPopularPapers] = useState([])
  const [recentNotices, setRecentNotices] = useState([])
  const [recentNews, setRecentNews] = useState([])
  const [topContributors, setTopContributors] = useState([])
  const [loading, setLoading] = useState(true)


  useEffect(() => {
    Promise.all([
      getClasses(),
      getRecentPapers(10),
      getPopularPapers(10),
      getRecentNotices(6, true),
      getRecentNews(6),
      getLeaderboard(5).catch(() => ({ data: [] })),
    ])
      .then(([clsRes, recentRes, popularRes, noticesRes, newsRes, lbRes]) => {
        setClasses(clsRes.data || [])
        setRecentPapers(recentRes.data || [])
        setPopularPapers(popularRes.data || [])
        setRecentNotices(noticesRes.data || [])
        setRecentNews(newsRes.data || [])
        setTopContributors(lbRes.data || [])
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

      {/* Submit Material CTA */}
      <section className="bg-blue-50 border-b border-blue-100">
        <div className="max-w-4xl mx-auto px-4 py-8 text-center flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-left">
            <h3 className="text-xl font-bold text-gray-900">Have a question paper or answer key?</h3>
            <p className="text-gray-600 mt-1">Share it with other Tamil Nadu students and help the community.</p>
          </div>
          <Link to="/submit-material" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold transition-colors shadow-sm whitespace-nowrap">
            Submit Material
          </Link>
        </div>
      </section>

      {/* ── Top Contributors Spotlight ── */}
      {!loading && topContributors.filter(c => (c.approved_count ?? c.accepted_contributions ?? 0) > 0).length > 0 && (
        <section className="bg-white border-b border-gray-100">
          <div className="max-w-4xl mx-auto px-4 py-8">
            <div className="bg-gradient-to-r from-amber-50/70 via-white to-amber-50/40 rounded-3xl border border-amber-200/80 p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-5">
              <div className="space-y-1 text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start gap-2">
                  <span className="text-xl">🏆</span>
                  <h2 className="text-lg font-extrabold text-gray-900">Top Contributors</h2>
                </div>
                <div className="flex flex-wrap items-center justify-center sm:justify-start gap-x-3 gap-y-1.5 pt-1 text-xs sm:text-sm text-gray-800">
                  {topContributors
                    .filter(c => (c.approved_count ?? c.accepted_contributions ?? 0) > 0)
                    .slice(0, 5)
                    .map((c, i, arr) => (
                      <span key={c.contributor_name || i} className="inline-flex items-center font-semibold text-gray-900">
                        <span>{c.contributor_name}</span>
                        {i < arr.length - 1 && <span className="ml-3 text-gray-300 font-normal select-none">•</span>}
                      </span>
                    ))}
                </div>
              </div>
              <Link
                to="/leaderboard"
                className="shrink-0 px-4 py-2 bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold text-xs rounded-xl transition shadow-2xs"
              >
                View Leaderboard →
              </Link>
            </div>
          </div>
        </section>
      )}


      {/* ── Latest Official Notices ── */}
      {!loading && recentNotices.length > 0 && (
        <section className="bg-gradient-to-br from-indigo-50 to-blue-50 border-t border-indigo-100">
          <div className="max-w-6xl mx-auto px-4 py-10">
            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <span>📢</span> Latest Official Notices
                </h2>
                <p className="text-gray-500 text-sm mt-1">Timetables, results, circulars, and important announcements</p>
              </div>
              <Link
                to="/official-notices"
                className="text-sm text-indigo-600 hover:text-indigo-800 font-semibold hidden sm:flex items-center gap-1"
              >
                View All →
              </Link>
            </div>

            {/* Featured pinned notice banner */}
            {recentNotices.find(n => n.is_pinned) && (() => {
              const pinned = recentNotices.find(n => n.is_pinned)
              const icon = CATEGORY_ICONS[pinned.category] ?? '📄'
              return (
                <Link
                  to={`/notice/${pinned.id}`}
                  className="flex items-center gap-4 bg-white border border-amber-200 rounded-2xl p-4 mb-5 shadow-sm hover:shadow-md transition-shadow group"
                >
                  <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center text-2xl shrink-0">
                    {icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">📌 Featured Notice</span>
                      <span className="text-xs text-gray-400">{pinned.category}</span>
                    </div>
                    <p className="font-bold text-gray-900 group-hover:text-indigo-700 transition-colors truncate">{pinned.title}</p>
                  </div>
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              )
            })()}

            {/* Compact notice list */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm divide-y divide-gray-50 overflow-hidden">
              {recentNotices.filter(n => !n.is_pinned).slice(0, 5).map(notice => (
                <NoticeCard key={notice.id} notice={notice} compact />
              ))}
            </div>

            <div className="mt-4 text-center sm:hidden">
              <Link to="/official-notices" className="text-sm text-indigo-600 hover:text-indigo-800 font-semibold">
                View All Official Notices →
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Latest Education News ── */}
      {!loading && recentNews.length > 0 && (
        <section className="bg-white border-t border-gray-100">
          <div className="max-w-6xl mx-auto px-4 py-10">
            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <span>📰</span> Latest Education News
                </h2>
                <p className="text-gray-500 text-sm mt-1">Holiday announcements, exam updates, government circulars, and more</p>
              </div>
              <Link
                to="/news"
                className="text-sm text-blue-600 hover:text-blue-800 font-semibold hidden sm:flex items-center gap-1"
              >
                View All →
              </Link>
            </div>

            {/* Compact news list */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm divide-y divide-gray-50 overflow-hidden">
              {recentNews.slice(0, 6).map(article => (
                <NewsCard key={article.id} article={article} compact />
              ))}
            </div>

            <div className="mt-4 text-center sm:hidden">
              <Link to="/news" className="text-sm text-blue-600 hover:text-blue-800 font-semibold">
                View All News →
              </Link>
            </div>
          </div>
        </section>
      )}

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
