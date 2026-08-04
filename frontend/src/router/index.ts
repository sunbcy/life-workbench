import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '为你推荐', icon: '✨' },
    },
    {
      path: '/feed',
      name: 'feed',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '推荐流', icon: '✨' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfilePage.vue'),
      meta: { title: '我的画像', icon: '🧬' },
    },
    {
      path: '/interest-map',
      name: 'interest-map',
      component: () => import('@/views/InterestMap.vue'),
      meta: { title: '兴趣地图', icon: '🌳' },
    },
    {
      path: '/price',
      name: 'price-compare',
      component: () => import('@/views/PriceCompare.vue'),
      meta: { title: '比价', icon: '💰' },
    },
    {
      path: '/nearby',
      name: 'nearby',
      component: () => import('@/views/NearbyResources.vue'),
      meta: { title: '周边', icon: '📍' },
    },
    {
      path: '/news',
      name: 'news',
      component: () => import('@/views/NewsInfo.vue'),
      meta: { title: '资讯', icon: '📰' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
      meta: { title: '配置管理', icon: '⚙️' },
    },
  ],
})

router.afterEach((to) => {
  document.title = `${to.meta.title} - 生活工作台`
})

export default router
