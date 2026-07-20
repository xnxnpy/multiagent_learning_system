<template>
  <el-config-provider>
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElConfigProvider } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const userStore = useUserStore()

onMounted(() => {
  // 页面加载时从 localStorage 恢复用户状态
  userStore.initFromStorage()
})
</script>

<style>
#app {
  width: 100%;
  height: 100vh;
}
</style>
