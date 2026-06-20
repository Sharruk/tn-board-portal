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
  axios.post('/api/v1/auth/login', { username, password })

export const getAdminPapers = () => adminApi.get('/admin/papers')

export const uploadPaper = (formData) =>
  adminApi.post('/admin/papers', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const updatePaper = (id, data) => adminApi.put(`/admin/papers/${id}`, data)

export const deletePaper = (id) => adminApi.delete(`/admin/papers/${id}`)

export default adminApi
