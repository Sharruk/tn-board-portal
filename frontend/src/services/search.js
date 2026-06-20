import api from './api'

export const searchPapers = (params) => api.get('/search', { params })
