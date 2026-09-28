<template>
  <AppLayout
    :menu-items="menuItems"
    portal-title="教师教研中心"
    portal-type="teacher"
    portal-color="#3D6B4F"
    avatar-color="#3D6B4F"
  >
    <router-view />
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from './AppLayout.vue'

const menuItems = [
  // 教学
  { key: 'courses', label: '课程管理', group: '教学' },
  { key: 'assignments', label: '作业管理', group: '教学' },
  // 学情与干预
  { key: 'analytics', label: '班级学情', group: '学情与干预' },
  // 资源治理
  { key: 'resources', label: '资源审核', group: '资源治理' },
  { key: 'knowledge', label: '共享知识库', group: '资源治理' },
]
</script>
