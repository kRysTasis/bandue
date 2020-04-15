import Vue from 'vue'
import RegisterWrap from './RegisterWrap'
import router from '@/router'
import vuetify from '../../plugins/vuetify'
import 'vuetify/dist/vuetify.min.css'
require('@/static/scss/main.scss')

Vue.config.productionTip = false

// 以下でグローバルコンポーネントの登録をしている
// 第一引数に名前を指定して、DjangoのHTML側で<signup></signup>でコンポーネントを呼び出す事ができる
Vue.component('register-wrap', RegisterWrap)

new Vue({
	vuetify,
	router,
	data: {

	},
	methods: {

	}
}).$mount('#register')