<template>
  <AppLayout
    :menu-items="menuItems"
    portal-title="教师端"
    portal-type="teacher"
    portal-color="#059669"
    avatar-color="#059669"
  >
    <router-view />
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from './AppLayout.vue'

const menuItems = [
  { key: 'courses', label: '课程管理' },
  { key: 'resources', label: '资源审核' },
  { key: 'assignments', label: '作业管理' },
  { key: 'analytics', label: '班级学情' },
  { key: 'knowledge', label: '知识库' },
]
</script>
