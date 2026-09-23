<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Article, type ArticleStatus } from '../api/client'

const STATUS: { value?: ArticleStatus; label: string }[] = [
  { label: '全部' },
  { value: 'ingested', label: '待审' },
  { value: 'approved', label: '已审' },
  { value: 'rejected', label: '拒绝' },
  { value: 'published', label: '已发' },
]

const items = ref<Article[]>([])
const current = ref<Article | null>(null)
const filter = ref<ArticleStatus | undefined>()
const error = ref('')
const notice = ref('')
const polishing = ref(false)
const polishStyle = ref('专业、真诚、克制，适合健身减脂与个人成长类公众号')

async function load() {
  error.value = ''
  items.value = await api.listArticles(filter.value)
}

function select(item: Article) {
  current.value = { ...item }
}

async function save() {
  if (!current.value) return
  error.value = ''
  current.value = await api.updateArticle(current.value.id, {
    title: current.value.title,
    summary: current.value.summary,
    body_html: current.value.body_html,
    author: current.value.author,
  })
  notice.value = '已保存'
  await load()
}

async function approve() {
  if (!current.value) return
  current.value = await api.approve(current.value.id)
  await load()
}

async function reject() {
  if (!current.value) return
  current.value = await api.reject(current.value.id)
  await load()
}

async function polish() {
  if (!current.value) return
  polishing.value = true
  error.value = ''
  notice.value = ''
  try {
    current.value = await api.polish(current.value.id, polishStyle.value)
    notice.value = 'AI 润色与公众号排版已完成，请人工复核后再审核'
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'AI 润色失败'
  } finally {
    polishing.value = false
  }
}

async function publish() {
  if (!current.value) return
  error.value = ''
  notice.value = ''
  try {
    const result = await api.publish(current.value.id)
    notice.value = result.message
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发布失败'
  }
}

onMounted(load)
</script>

<template>
  <section class="split">
    <div>
      <header>
        <h2>稿件</h2>
        <div class="filters">
          <button
            v-for="item in STATUS"
            :key="item.label"
            :class="{ active: filter === item.value }"
            @click="filter = item.value; load()"
          >
            {{ item.label }}
          </button>
        </div>
      </header>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="notice" class="ok">{{ notice }}</p>
      <ul class="list">
        <li
          v-for="item in items"
          :key="item.id"
          :class="{ selected: current?.id === item.id }"
          @click="select(item)"
        >
          <strong>{{ item.title }}</strong>
          <small>{{ item.status }} · 质量 {{ item.quality_score }}</small>
        </li>
      </ul>
      <p v-if="!items.length" class="muted">暂无稿件，请先抓取。</p>
    </div>
    <div v-if="current" class="editor">
      <label>标题</label>
      <input v-model="current.title" />
      <label>作者</label>
      <input v-model="current.author" />
      <label>摘要</label>
      <textarea v-model="current.summary" rows="3" />
      <label>正文 HTML</label>
      <textarea v-model="current.body_html" rows="12" />
      <p class="muted">来源：<a :href="current.source_url" target="_blank">{{ current.source_url }}</a></p>
      <label>AI 润色风格</label>
      <input v-model="polishStyle" />
      <div class="actions">
        <button @click="save">保存</button>
        <button :disabled="polishing" @click="polish">
          {{ polishing ? '润色中…' : 'AI 润色并排版' }}
        </button>
        <button @click="approve">审核通过</button>
        <button class="ghost" @click="reject">拒绝</button>
        <button class="primary" @click="publish">发布到公众号</button>
      </div>
    </div>
  </section>
</template>
