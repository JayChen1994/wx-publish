<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api/client'

export interface Draft {
  title: string
  summary: string
  body_html: string
  source_url: string
  author: string
}

const error = ref('')
const notice = ref('')
const fetching = ref(false)
const polishing = ref(false)
const publishing = ref(false)
const polishStyle = ref('专业、真诚、克制，适合健身减脂与个人成长类公众号')
const autoPublish = ref(false)

const publishButtonLabel = computed(() =>
  autoPublish.value ? '发表到公众号' : '保存到微信草稿箱',
)
const runAllButtonLabel = computed(() =>
  autoPublish.value ? '润色并发表' : '润色并保存草稿',
)

const linkForm = reactive({
  title: '',
  source_url: '',
  author: '',
  body_html: '',
})

const draft = ref<Draft | null>(null)

const articlePreview = computed(() => draft.value?.body_html ?? '')

async function fetchPreview() {
  error.value = ''
  notice.value = ''
  fetching.value = true
  try {
    draft.value = await api.fetchDraft({
      title: linkForm.title,
      source_url: linkForm.source_url,
      author: linkForm.author,
      body_html: linkForm.body_html,
    })
    notice.value = linkForm.body_html.trim()
      ? '已按粘贴内容去水印，可预览后保存草稿'
      : '已抓取并去水印，可直接编辑预览后保存草稿'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '抓取失败'
  } finally {
    fetching.value = false
  }
}

async function polish() {
  if (!draft.value) return
  polishing.value = true
  error.value = ''
  notice.value = ''
  try {
    draft.value = await api.polishDraft({ ...draft.value, style: polishStyle.value })
    notice.value = 'AI 润色完成，请核对预览后再发布'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'AI 润色失败'
  } finally {
    polishing.value = false
  }
}

async function publish() {
  if (!draft.value) return
  publishing.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await api.publishDraft(draft.value)
    notice.value = result.message
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发布失败'
  } finally {
    publishing.value = false
  }
}

async function runAll() {
  if (!draft.value) return
  publishing.value = true
  error.value = ''
  notice.value = ''
  try {
    draft.value = await api.polishDraft({ ...draft.value, style: polishStyle.value })
    const result = await api.publishDraft(draft.value)
    notice.value = result.message
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发布失败'
  } finally {
    publishing.value = false
  }
}

onMounted(async () => {
  try {
    const health = await api.health()
    autoPublish.value = health.auto_publish
  } catch {
    autoPublish.value = false
  }
})
</script>

<template>
  <section class="page">
    <header>
      <h2>复制发布</h2>
      <p>
        填标题和原文链接 → 抓取预览（图片去水印）→ 编辑 → 润色 →
        {{ autoPublish ? '提交微信发表（AUTO_PUBLISH 已开）' : '保存微信草稿箱' }}。不落本地稿件库。
      </p>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="ok">{{ notice }}</p>

    <form class="editor entry" @submit.prevent="fetchPreview">
      <label>标题</label>
      <input v-model="linkForm.title" placeholder="可与原文不同，抓取后会保留你填的标题" />
      <label>原文链接</label>
      <input v-model="linkForm.source_url" placeholder="https://mp.weixin.qq.com/s/..." required />
      <label>原作者（可选）</label>
      <input v-model="linkForm.author" />
      <label>正文（可选，抓取失败时用）</label>
      <textarea
        v-model="linkForm.body_html"
        rows="6"
        placeholder="在微信里打开文章 → 全选复制 → 粘贴到这里（含图片）。填了此项会跳过链接抓取。"
      />
      <button type="submit" :disabled="fetching">
        {{ fetching ? '抓取中…' : '抓取预览' }}
      </button>
    </form>

    <div v-if="draft" class="split later">
      <div class="editor">
        <label>标题</label>
        <input v-model="draft.title" />
        <label>摘要</label>
        <textarea v-model="draft.summary" rows="3" />
        <label>正文 HTML（可改）</label>
        <textarea v-model="draft.body_html" rows="10" />
        <label>AI 润色风格</label>
        <input v-model="polishStyle" />
        <div class="actions">
          <button type="button" :disabled="polishing" @click="polish">
            {{ polishing ? '润色中…' : 'AI 润色' }}
          </button>
          <button type="button" class="primary" :disabled="publishing" @click="publish">
            {{ publishing ? '提交中…' : publishButtonLabel }}
          </button>
          <button type="button" :disabled="publishing" @click="runAll">
            {{ publishing ? '处理中…' : runAllButtonLabel }}
          </button>
        </div>
      </div>
      <div class="editor">
        <h3>文章预览</h3>
        <div class="preview" v-html="articlePreview" />
      </div>
    </div>
  </section>
</template>
