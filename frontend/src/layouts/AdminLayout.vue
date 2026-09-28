<template>
  <AppLayout
    :menu-items="menuItems"
    portal-title="管理控制台"
    portal-type="admin"
    portal-color="#70293C"
    avatar-color="#70293C"
  >
    <router-view />
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from './AppLayout.vue'

const menuItems = [
  // 治理分析
  { key: 'analytics', label: '学习分析', group: '治理分析' },
  { key: 'knowledge', label: '知识库运维', group: '治理分析' },
  { key: 'content-security', label: '内容安全', group: '治理分析' },
  // 平台配置
  { key: 'users', label: '用户管理', group: '平台配置' },
  { key: 'models', label: '模型管理', group: '平台配置' },
  { key: 'config', label: '系统配置', group: '平台配置' },
  // 运维
  { key: 'logs', label: '日志查看', group: '运维' },
  { key: 'backup', label: '数据备份', group: '运维' },
  { key: 'showcase', label: '系统验证', group: '运维' },
]
</script>
