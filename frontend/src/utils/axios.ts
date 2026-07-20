import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers = config.headers || {}
      config.headers['Authorization'] = `Bearer ${token}`
    }
    // FormData 不设置 Content-Type，让浏览器自动带上 boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response) {
      const { status, data } = error.response

      switch (status) {
        case 401:
          // 只有在当前页面不是登录页时才跳转，避免循环
          if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            localStorage.removeItem('userRole')
            ElMessage.error(data?.detail || '登录已过期，请重新登录')
            router.push('/login')
          }
          break
        case 403:
          ElMessage.error(data?.detail || '没有权限访问')
          break
        case 404:
          ElMessage.error(data?.detail || '资源不存在')
          break
        case 409:
          ElMessage.error(data?.detail || '资源冲突')
          break
        default:
          ElMessage.error(data?.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default request
