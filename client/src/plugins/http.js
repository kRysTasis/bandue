import Vue from 'vue'
import axios from 'axios'

export default {
	install: function (Vue, options) {
		// デフォルト定義
		const http = axios.create({
			baseURL: 'http://192.168.33.12:8000/',
			xsrfCookieName:'csrftoken',
			xsrfHeaderName: 'X-CSRFTOKEN',
			timeout: 10000,
		})
		// リクエストのデフォルト定義
		http.interceptors.request.use((config) => {
			console.log('リクエスト情報', config)
			// ヘッダーに認証済みのToken埋め込み
			if (Vue.prototype.$store.state.isAuth) {
				config.headers = {
					Authorization: `JWT ${Vue.prototype.$store.state.token}`,
					'Content-Type': 'application/json'
				}
				if (config.method === 'get') config.params.loginUser = Vue.prototype.$store.state.loginUser
			}
			return config
		})
		// レスポンスのデフォルト定義
		http.interceptors.response.use((res) => {
			// リクエストデータのJSON解析
			var requestData = (res.config.data !== undefined) ? JSON.parse(res.config.data) : null
			res.requestData = requestData

			return res
		})
		Vue.prototype.$axios = http
	}
}
