<template>
  <AppLayout
    :menu-items="menuItems"
    portal-title="学生端"
    portal-type="student"
    portal-color="#1E88E5"
    avatar-color="#1E88E5"
    :enable-notifications="true"
  >
    <router-view />
  </AppLayout>
  <TutorFloatingButton />
  <WorkflowBubble />
</template>

<script setup lang="ts">
import AppLayout from './AppLayout.vue'
import TutorFloatingButton from '@/components/tutor/TutorFloatingButton.vue'
import WorkflowBubble from '@/components/WorkflowBubble.vue'

const menuItems = [
  { key: 'profile', label: '学习画像' },
  { key: 'learning-path', label: '学习路径' },
  { key: 'resources', label: '学习资源' },
  { key: 'tutor', label: '智能辅导' },
  { key: 'report', label: '学习报告' },
  { key: 'notifications', label: '通知' },
  { key: 'my-learning', label: '我的学习记录' }
]
</script>
