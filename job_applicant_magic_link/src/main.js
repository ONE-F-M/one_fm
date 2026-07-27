import './index.css'

import { createApp } from 'vue'
import App from './App.vue'

import { Button, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'


let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(resourcesPlugin)

app.component('Button', Button)
app.mount('#app')
