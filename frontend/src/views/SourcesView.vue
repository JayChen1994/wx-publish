<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, type Source } from '../api/client'

const sources = ref<Source[]>([])
const error = ref('')
const form = reactive({ name: '', url: '', topics: '健身减脂,人生感悟' })

async function load() {
  error.value = ''
  try {
    sources.value = await api.listSources()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
}

async function create() {
  error.value = ''
  try {
    await api.createSource(form)
    form.name = ''
    form.url = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建失败'
  }
}

async function remove(id: string) {
  await api.deleteSource(id)
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <header>
      <h2>RSS 来源</h2>
      <p>优先使用公开 RSS。只采集你有权使用或已获授权的内容。</p>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <form class="form" @submit.prevent="create">
      <input v-model="form.name" placeholder="名称" required />
      <input v-model="form.url" placeholder="https://example.com/rss" required />
      <input v-model="form.topics" placeholder="主题标签" />
      <button type="submit">添加</button>
    </form>
    <table v-if="sources.length">
      <thead>
        <tr>
          <th>名称</th>
          <th>URL</th>
          <th>主题</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in sources" :key="item.id">
          <td>{{ item.name }}</td>
          <td class="url">{{ item.url }}</td>
          <td>{{ item.topics }}</td>
          <td><button class="ghost" @click="remove(item.id)">删除</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">暂无来源</p>
  </section>
</template>
