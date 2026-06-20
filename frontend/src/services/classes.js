import api from './api'

export const getClasses = () => api.get('/classes')
export const getClass = (id) => api.get(`/classes/${id}`)
export const getSubjectsForClass = (id) => api.get(`/classes/${id}/subjects`)
