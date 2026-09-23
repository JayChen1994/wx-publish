<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Health } from '../api/client'

const health = ref<Health | null>(null)
const ingestMsg = ref('')
const error = ref('')
const loading = ref(false)

async function load() {
  error.value = ''
  try {
    health.value = await api.health()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '无法连接后端'
  }
}

async function ingest() {
  loading.value = true
  ingestMsg.value = ''
  error.value = ''
  try {
    const result = await api.ingest()
    ingestMsg.value = `新增 ${result.created} 篇，跳过重复 ${result.skipped} 篇`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '抓取失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <header>
      <h2>工作台</h2>
      <p>健身减脂与人生感悟内容流水线。默认只建草稿，需审核后发布。</p>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="cards" v-if="health">
      <article>
        <span>后端</span>
        <strong>{{ health.status }}</strong>
      </article>
      <article>
        <span>微信凭证</span>
        <strong>{{ health.wechat_configured ? '已配置' : '未配置' }}</strong>
      </article>
      <article>
        <span>AI 润色</span>
        <strong>{{ health.llm_configured ? '已配置' : '未配置' }}</strong>
      </article>
      <article>
        <span>自动群发</span>
        <strong>{{ health.auto_publish ? '开启' : '关闭' }}</strong>
      </article>
    </div>
    <button :disabled="loading" @click="ingest">{{ loading ? '抓取中…' : '立即抓取全部来源' }}</button>
    <p v-if="ingestMsg" class="ok">{{ ingestMsg }}</p>
  </section>
</template>
