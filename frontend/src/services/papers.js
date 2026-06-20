import api from './api'

export const getPaper = (id) => api.get(`/papers/${id}`)
export const getPaperBySlug = (slug) => api.get(`/papers/by-slug/${slug}`)
export const getRecentPapers = (limit = 10) => api.get('/papers/recent', { params: { limit } })
export const getPopularPapers = (limit = 10) => api.get('/papers/popular', { params: { limit } })
export const getExamTypes = () => api.get('/exam-types')
export const recordDownload = (id) => api.post(`/papers/${id}/download`)
