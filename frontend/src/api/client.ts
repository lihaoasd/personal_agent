import axios from 'axios'
import { ElMessage } from 'element-plus'

const baseURL: string = (import.meta.env.VITE_API_BASE as string) || '/api'

const client = axios.create({ baseURL, timeout: 60000 })

client.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const detail = err?.response?.data?.detail || err.message || '请求失败'
    ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    return Promise.reject(err)
  },
)

export default client
