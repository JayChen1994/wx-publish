import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import SourcesView from '../views/SourcesView.vue'
import ArticlesView from '../views/ArticlesView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/sources', name: 'sources', component: SourcesView },
    { path: '/articles', name: 'articles', component: ArticlesView },
  ],
})
