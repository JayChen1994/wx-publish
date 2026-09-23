<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="layout">
    <aside>
      <h1>FitLife</h1>
      <p class="tag">录入 · 润色 · 发布</p>
    </aside>
    <main>
      <RouterView />
    </main>
  </div>
</template>
