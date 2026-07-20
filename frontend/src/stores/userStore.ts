import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isTeacher = computed(() => user.value?.role === 'teacher')
  const isStudent = computed(() => user.value?.role === 'student')

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUser(newUser: User, newToken?: string) {
    user.value = newUser
    localStorage.setItem('user', JSON.stringify(newUser))
    localStorage.setItem('userRole', newUser.role)
    if (newToken) {
      localStorage.setItem('token', newToken)
      token.value = newToken
    }
  }

  function login(newToken: string, newUser: User) {
    setToken(newToken)
    setUser(newUser, newToken)
  }

  function logout() {
    token.value = ''
    user.value = null
    // 清除所有用户相关数据，避免跨账号残留
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('userRole')
    localStorage.removeItem('student_resources')
    localStorage.removeItem('learning_path_current_stage')
  }

  function initFromStorage() {
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    
    if (storedToken) {
      token.value = storedToken
    }
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch (e) {
        console.error('Failed to parse stored user:', e)
      }
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    isTeacher,
    isStudent,
    setToken,
    setUser,
    login,
    logout,
    initFromStorage
  }
})
