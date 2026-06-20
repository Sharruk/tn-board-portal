import api from './api'

export const getPaper = (id) => api.get(`/papers/${id}`)
export const getRecentPapers = (limit = 6) => api.get('/papers/recent', { params: { limit } })
export const getExamTypes = () => api.get('/exam-types')
export const recordDownload = (id) => api.post(`/papers/${id}/download`)
