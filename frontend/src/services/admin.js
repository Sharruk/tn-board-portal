import axios from 'axios'

const TOKEN_KEY = 'adminToken'

const adminApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 60000,
})

adminApi.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

adminApi.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = '/admin/login'
    }
    return Promise.reject(err)
  }
)

export const adminLogin = (username, password) =>
  adminApi.post('/auth/login', { username, password })

export const getAdminPapers = () => adminApi.get('/admin/papers')

export const uploadPaper = (formData, onProgress) =>
  adminApi.post('/admin/papers', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    },
  })

export const updatePaper = (id, data) => adminApi.put(`/admin/papers/${id}`, data)

export const deletePaper = (id) => adminApi.delete(`/admin/papers/${id}`)

export const getSearchAnalytics = () => adminApi.get('/admin/search-analytics')

export const getRecentUploads = (limit = 20) => adminApi.get(`/admin/recent-uploads?limit=${limit}`)

export const getContentStatus = () => adminApi.get('/admin/content-status')

export const getAdminMe = () => adminApi.get('/admin/me')

export const getAuditLogs = (limit = 50, action = null) => {
  const params = new URLSearchParams({ limit })
  if (action) params.append('action', action)
  return adminApi.get(`/admin/audit-logs?${params}`)
}

export default adminApi
