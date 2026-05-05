import { createRouter, createWebHistory } from 'vue-router'

import PlannerView from '../views/PlannerView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'planner',
      component: PlannerView
    }
  ],
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth', top: 16 }
    }
    return { top: 0 }
  }
})

export default router

