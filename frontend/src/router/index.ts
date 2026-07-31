import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/pages/auth/Landing.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/auth/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/pages/auth/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/student',
    component: () => import('@/layouts/StudentLayout.vue'),
    meta: { requiresAuth: true, roles: ['student', 'teacher', 'admin'] },
    children: [
      {
        path: '',
        redirect: '/student/profile'
      },
      {
        path: 'profile',
        name: 'StudentProfile',
        component: () => import('@/pages/student/Profile.vue')
      },
      {
        path: 'learning-path',
        name: 'LearningPath',
        component: () => import('@/pages/student/LearningPath.vue')
      },
      {
        path: 'resources',
        name: 'StudentResources',
        component: () => import('@/pages/student/Resources.vue')
      },
      {
        path: 'tutor',
        name: 'StudentTutor',
        component: () => import('@/pages/student/Tutor.vue')
      },
      {
        path: 'report',
        name: 'StudentReport',
        component: () => import('@/pages/student/Report.vue')
      },
      {
        path: 'notifications',
        name: 'StudentNotifications',
        component: () => import('@/pages/student/Notifications.vue')
      },
      {
        path: 'my-learning',
        name: 'MyLearning',
        component: () => import('@/pages/student/MyLearning.vue')
      }
    ]
  },
  {
    path: '/teacher',
    component: () => import('@/layouts/TeacherLayout.vue'),
    meta: { requiresAuth: true, roles: ['teacher', 'admin'] },
    children: [
      {
        path: '',
        redirect: '/teacher/courses'
      },
      {
        path: 'courses',
        name: 'TeacherCourses',
        component: () => import('@/pages/teacher/Courses.vue')
      },
      {
        path: 'resources',
        name: 'TeacherResources',
        component: () => import('@/pages/teacher/Resources.vue')
      },
      {
        path: 'analytics',
        name: 'TeacherAnalytics',
        component: () => import('@/pages/teacher/Analytics.vue')
      },
      {
        path: 'knowledge',
        name: 'TeacherKnowledge',
        component: () => import('@/pages/teacher/Knowledge.vue')
      },
      {
        path: 'assignments',
        name: 'TeacherAssignments',
        component: () => import('@/pages/teacher/Assignments.vue')
      },
      {
        path: 'profile',
        name: 'TeacherProfile',
        component: () => import('@/pages/auth/Profile.vue')
      }
    ]
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
    children: [
      {
        path: '',
        redirect: '/admin/users'
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/pages/admin/Users.vue')
      },
      {
        path: 'profile',
        name: 'AdminProfile',
        component: () => import('@/pages/admin/Profile.vue')
      },
      {
        path: 'content-review',
        name: 'AdminContentReview',
        redirect: '/admin/content-security'
      },
      {
        path: 'config',
        name: 'AdminConfig',
        component: () => import('@/pages/admin/Config.vue')
      },
      {
        path: 'models',
        name: 'AdminModels',
        component: () => import('@/pages/admin/Models.vue')
      },
      {
        path: 'logs',
        name: 'AdminLogs',
        component: () => import('@/pages/admin/Logs.vue')
      },
      {
        path: 'content-security',
        name: 'AdminContentSecurity',
        component: () => import('@/pages/admin/ContentSecurity.vue')
      },
      {
        path: 'showcase',
        name: 'AdminShowcase',
        component: () => import('@/pages/admin/Showcase.vue')
      },
      {
        path: 'backup',
        name: 'AdminBackup',
        component: () => import('@/pages/admin/Backup.vue')
      }
    ]
  },
  {
    path: '/profile',
    name: 'UserProfile',
    component: () => import('@/pages/auth/Profile.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userRole = localStorage.getItem('userRole')

  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  if (to.meta.roles && userRole && Array.isArray(to.meta.roles) && !to.meta.roles.includes(userRole)) {
    const roleRoutes: Record<string, string> = {
      student: '/student',
      teacher: '/teacher',
      admin: '/admin'
    }
    next(roleRoutes[userRole] || '/login')
    return
  }

  if ((to.path === '/' || to.path === '/login' || to.path === '/register') && token && userRole) {
    const roleRoutes: Record<string, string> = {
      student: '/student',
      teacher: '/teacher',
      admin: '/admin'
    }
    next(roleRoutes[userRole] || '/')
    return
  }

  next()
})

export default router
