<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="layout">
    <aside>
      <h1>FitLife</h1>
      <p class="tag">采集 · 审核 · 公众号</p>
      <nav>
        <RouterLink to="/">总览</RouterLink>
        <RouterLink to="/sources">来源</RouterLink>
        <RouterLink to="/articles">稿件</RouterLink>
      </nav>
    </aside>
    <main>
      <RouterView />
    </main>
  </div>
</template>
