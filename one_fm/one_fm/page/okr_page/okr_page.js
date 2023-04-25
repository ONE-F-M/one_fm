
frappe.pages['okr-page'].on_page_load = function(wrapper) {
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
	let scrtag_ = document.createElement('script');
	scrtag_.src = "https://cdn.jsdelivr.net/npm/daterangepicker/daterangepicker.min.js"
	scrtag_.type = "text/javascript";
	document.body.appendChild(scrtag_);
	let scrtag_m = document.createElement('script');
	scrtag_m.src = "https://cdn.jsdelivr.net/momentjs/latest/moment.min.js"
	scrtag_m.type = "text/javascript";
	document.body.appendChild(scrtag_m);
	
	// create page layer
	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('okr_page'));
	setTimeout(()=>{
		const app = Vue.createApp(
			{	
				delimiters: ['[%', '%]'],
				
				data() {
					return {
						selectedOption: '',
						assignedOption:'',
						priorityOption:'',
						selectedOption2: '',
						assignedOption2:'',
						priorityOption2:'',
						doctype_options: [
						{ label: 'Reference Doctype 1', value: 'option1' },
						{ label: 'Reference Doctype 2', value: 'option2' },
						{ label: 'Reference Doctype 3', value: 'option3' },
						],
						user_options: [
							{ label: 'User  1', value: 'option4' },
							{ label: 'User  2', value: 'option5' },
							{ label: 'User  3', value: 'option7' },
							],
						priority_list:[
							{ label: 'Priority  1', value: 'option4' },
							{ label: 'Priority  2', value: 'option5' },
							{ label: 'Priority  3', value: 'option7' },
							],
						email: '',
						first_name: '',
						last_name: '',
						phone: '',
						
					}
				},
				mounted(){
					
					this.getProfile();
					
					// show page content
					document.querySelector("#app-container").style.display = "block";
					

				},
				methods: {
					setup_libs(){
						$('.start-date').datepicker({
							language:'en',
							dateFormat:'dd.mm.yyyy'
							
						  });
						  
						  $('.end-date').datepicker({
							language:'en',
							format:'dd.mm.yyyy',
							dateFormat:'dd.mm.yyyy'
						  
						  });	
						  $('#datefields1, #datefields2').click(function() {
							
							if ($(this).attr('id') == 'datefields1') {
							  console.log('First')
							} else if ($(this).attr('id') == 'datefields2') {
								console.log('SECOND')
							}
						  });
							},
					getProfile(){
						
						let me = this;
						frappe.call({
							method: "one_fm.one_fm.page.okr_page.okr_page.get_profile", //dotted path to server method
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
						this.setup_libs()
						
					}
				}
			}
		)
		app.mount('#OKR-APP')
	}, 5000)
}
