frappe.pages['okr'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'OKR',
		single_column: true
	});
	// add css

	// initialize html with vue
	let scrtag = document.createElement('script');
	scrtag.src = "https://unpkg.com/vue@3/dist/vue.global.js"
	scrtag.type = "text/javascript";
  	document.body.appendChild(scrtag);
	// create page layer
	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('okr'));
	setTimeout(()=>{
		const app = Vue.createApp(
			{	
				delimiters: ['[%', '%]'],
				data() {
					return {
						email: '',
						first_name: '',
						last_name: '',
						phone: ''
					}
				},
				mounted(){
					this.getProfile();
				},
				methods: {
					getProfile(){
						let me = this;
						frappe.call({
							method: "one_fm.one_fm.page.okr.okr.get_profile", //dotted path to server method
							callback: function(r) {
								// code snippet
								if (r.message){
									let res = r.message;
									me.first_name = res.first_name;
									me.last_name = res.last_name;
									me.email = res.email;
								}
							}
						});
					}
				}
			}
		)
		app.mount('#OKR-APP')
	}, 5000)
}
