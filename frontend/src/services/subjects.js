import api from './api'

export const getSubject = (id) => api.get(`/subjects/${id}`)
export const getPapersForSubject = (id, params = {}) =>
  api.get(`/subjects/${id}/papers`, { params })
