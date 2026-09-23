import { createRouter, createWebHistory } from 'vue-router'
import ArticlesView from '../views/ArticlesView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', name: 'home', component: ArticlesView }],
})
