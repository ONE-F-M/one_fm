frappe.require([
	'/assets/one_fm/js/vue.global.js',
	'/assets/one_fm/js/daterangepicker.min.js',
	'/assets/one_fm/js/roster_js/select2.min.js',
	'/assets/one_fm/css/ows/ows.css',
	'/assets/one_fm/css/ows/daterangepicker.css',
	], () => {
    // chat.js and chat.css are loaded

})

frappe.pages['ows'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'OWS',
		single_column: true
	});
	// create page layer
	$(wrapper).find('.layout-main-section').empty().append(frappe.render_template('ows'));
	setTimeout(()=>{
		const app = Vue.createApp(
			{
				delimiters: ['[%', '%]'],
				data() {
					return {
						todo_pane: {
							name: ''
						},
						my_todos: [],
						assigned_todos: [],
						scrum_projects: [],
						personal_projects: [],
						active_repetitive_projects: [],
						my_todo_filters : new Object,
						assigned_todo_filters : new Object,
						doctype_ref:[],
						user_ref:[],
						company_objective: '',
						company_objective_quarter: '',
						my_objective: ''
					}
				},
				mounted(){
					// show page content
					this.loadSpinner(0);
					this.setupJS();
					this.getDefault()


					this.setupTriggers()

				},
				methods: {
					getAllFilters(){

						let me = this;

						me.my_todo_filters.name = $('#my_todos_id').val()

						me.my_todo_filters.assigned_by = $('#my_todos_assigned_by').val()

						me.my_todo_filters.reference_type = $('#my_todos_ref_type').val()

						me.my_todo_filters.date = $('#my_todos_date').val()
						me.my_todo_filters.priority = $('#my_todos_priority').val()
						me.assigned_todo_filters.name = $('#my_assigned_id').val()
						me.assigned_todo_filters.date = $('#my_assigned_date').val()
						me.assigned_todo_filters.reference_type = $('#assigned_reference_type').val()
						me.assigned_todo_filters.priority = $('#assigned_priority').val()
						me.assigned_todo_filters.allocated_to = $('#assigned_to').val()

						this.getDefault()

					},
					setupTriggers(){
						let me = this

						$('#my_todos_id').change(function(){
							me.getAllFilters()
						})

						$('#my_todos_ref_type').change(()=>{
							me.getAllFilters()
						})
						$('#my_todos_priority').on('change',function(){
							me.getAllFilters()
						})
						$('#my_todos_assigned_by').change(()=>{
							me.getAllFilters()
						})
						$('#my_assigned_id').change(()=>{

								me.getAllFilters()
							})

						$('#assigned_reference_type').change(()=>{
							me.getAllFilters()
						})
						$('#assigned_priority').change(()=>{
							me.getAllFilters()
						})
						$('#assigned_to').change(()=>{
							me.getAllFilters()
						})

					},
					setupFilters(is_my_todo){
						let me = this;

						let assigned_data = [{ 'id': '', 'text': 'Select Assigned' }]
						let reference_data = [{ 'id': '', 'text': 'Select Reference' }]
						let priotity_data = [{ 'id': '', 'text': 'Select Priority' },
											{ 'id': 'Low', 'text': 'Low' },
											{ 'id': 'Medium', 'text': 'Medium' },
											{ 'id': 'High', 'text': 'High' }]
						reference_data = reference_data.concat(me.doctype_ref)
						assigned_data = assigned_data.concat(me.user_ref)
						if(is_my_todo){

							$('#my_todos_ref_type').empty()
							$('#my_todos_assigned_by').empty()
							$('#my_todos_priority').empty()

							$('#my_todos_ref_type').select2({
								data:reference_data,
								width:'100%'
							})
							$('#my_todos_assigned_by').select2({
								data:assigned_data,
								width:'100%'
							})
							$('#my_todos_priority').select2({
								data:priotity_data,
								width:'100%'
							})
						}
						else{

							$('#assigned_reference_type').empty()
							$('#assigned_to').empty()
							$('#assigned_priority').empty()

							$('#assigned_reference_type').select2({
								data:reference_data,
								width:'100%'
							})
							$('#assigned_to').select2({
								data:assigned_data,
								width:'100%'
							})
							$('#assigned_priority').select2({
								data:priotity_data,
								width:'100%'
							})
						}
					},
					getDefault(){
						let me = this;

						frappe.call({
							method: "one_fm.one_fm.page.ows.ows.get_defaults",
							args: {
								args :[me.my_todo_filters,me.assigned_todo_filters] || [],
								has_todo_filter : Object.keys(me.my_todo_filters).length,
								has_assigned_filter : Object.keys(me.assigned_todo_filters).length
							},
							callback: function(r) {

								if (r.message){
									let res = r.message;
									me.company_objective =  res.company_objective;
									me.company_objective_quarter =  res.company_objective_quarter;
									me.my_objective =  res.my_objective;
									me.my_todos = res.my_todos;
									me.assigned_todos = res.assigned_todos;
									me.scrum_projects = res.scrum_projects;
									me.personal_projects = res.personal_projects;
									me.active_repetitive_projects = res.active_repetitive_projects;
									me.doctype_ref = res.filter_references[0]
									me.user_ref = res.filter_references[1]

									if(res.reset_filters == 1){
										me.setupFilters(1)
										me.setupFilters(0)
									}

								}
							}
						});
					},
					showTodo(todoType, todoName){
						// 1 = mytodo, 0 = assigned_todo
						let me = this;
						if (todoType==1){
							let todo = me.my_todos.filter(function(item){
							 return item.name==todoName;
							});
							if (todo.length>0){
								me.todo_pane = todo[0];
								me.todo_pane.url = frappe.urllib.get_base_url()+'/app/todo/'+me.todo_pane.name
							}
						} else {
							let todo = me.assigned_todos.filter(function(item){
							return item.name==todoName;
							});
							if (todo.length>0){
								me.todo_pane = todo[0];
								me.todo_pane.url = frappe.urllib.get_base_url()+'/app/todo/'+me.todo_pane.name
							}

						}
					},
					loadSpinner(state){
						if (state==0){
							document.querySelector("#app-container").style.display = "block";
							document.querySelector("#spinner").style.display = "none;";
						} else {
							document.querySelector("#app-container").style.display = "none";
							document.querySelector("#spinner").style.display = "block;";
						}

					},
					setupJS(){
						me = this
						$("#my_todos_date").datepicker({
							'language':'en',
							'autoClose':1,
							'dateFormat':'yyyy-mm-dd',
							onSelect: function(dateText) {
								me.getAllFilters()
							}
					  	}).datepicker('update', new Date(),
							);
						$("#my_assigned_date").datepicker({
							'language':'en',
							'autoClose':1,
							'dateFormat':'yyyy-mm-dd',
							onSelect: function(dateText) {
								me.getAllFilters()
							}
							}).datepicker('update', new Date(),
							);
					},
					 open_ref(link){

							window.open(link)
						},
					copyText(link_to_copy) {
						const show_success_alert = () => {
							frappe.show_alert({
								indicator: "green",
								message: __("Copied to clipboard."),
							});
						};
						const show_fail_alert = () => {
							frappe.show_alert({
								indicator: "red",
								message: __("Nothing to Copy."),
							});
						};
						if(link_to_copy == undefined){
							show_fail_alert();
						}
						else {
								if (navigator.clipboard && window.isSecureContext) {
									navigator.clipboard.writeText(link_to_copy).then(show_success_alert);
								}
						}
					}
				},
			}
		)
		app.mount('#OKR-APP')
	}, 5000)
}
