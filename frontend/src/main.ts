import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import './style.css'

// 前端入口只负责挂载应用和注册 Element Plus。
createApp(App).use(ElementPlus).mount('#app')
