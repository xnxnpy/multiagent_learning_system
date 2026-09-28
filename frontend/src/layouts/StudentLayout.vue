<template>
  <AppLayout
    :menu-items="menuItems"
    portal-title="学生学习中心"
    portal-type="student"
    portal-color="#B0512C"
    avatar-color="#B0512C"
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

/** 分节导航：对齐演示结构（学习中心 / 资源与练习 / 辅导与报告） */
const menuItems = [
  // 学习中心
  { key: 'profile', label: '学习画像', group: '学习中心' },
  { key: 'learning-path', label: '学习路径', group: '学习中心' },
  { key: 'resources', label: '学习资源', group: '学习中心' },
  { key: 'knowledge', label: '我的知识库', group: '学习中心' },
  // 资源与练习
  { key: 'question-bank', label: '题库', group: '资源与练习' },
  { key: 'wrong-book', label: '错题本', group: '资源与练习' },
  { key: 'notes', label: '学习笔记', group: '资源与练习' },
  { key: 'discovery', label: '学习发现', group: '资源与练习' },
  // 辅导与报告
  { key: 'tutor', label: '智能辅导', group: '辅导与报告' },
  { key: 'report', label: '学习报告', group: '辅导与报告' },
  { key: 'my-learning', label: '学习记录', group: '辅导与报告' },
  { key: 'plaza', label: '学习广场', group: '辅导与报告' },
  { key: 'notifications', label: '通知', group: '辅导与报告' },
]
</script>
