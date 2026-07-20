<template>
  <AppLayout
    :menu-items="menuItems"
    portal-title="管理端"
    portal-type="admin"
    portal-color="#DC2626"
    avatar-color="#DC2626"
  >
    <router-view />
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from './AppLayout.vue'

const menuItems = [
  { key: 'users', label: '用户管理' },
  { key: 'config', label: '系统配置' },
  { key: 'models', label: '模型管理' },
  { key: 'content-security', label: '内容安全审核' },
  { key: 'logs', label: '日志查看' },
  { key: 'backup', label: '数据备份' },
  { key: 'showcase', label: '系统验证' },
]
</script>
