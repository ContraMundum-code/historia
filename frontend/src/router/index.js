import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/persons', name: 'personList', component: () => import('../views/PersonList.vue') },
  { path: '/persons/:id', name: 'personDetail', component: () => import('../views/PersonDetail.vue') },
  { path: '/graph', name: 'graph', component: () => import('../views/KnowledgeGraph.vue') }
]

export default createRouter({ history: createWebHistory(), routes })
