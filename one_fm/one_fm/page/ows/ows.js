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
						all_todos: [],
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
						my_objective: '',
						okr_year: '',
						okr_quarter: ''
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
					fetchOKR(){
						let me = this;
						me.okr_year = $('#okr_year').val();
						me.okr_quarter = $('#okr_quarter').val();
						frappe.call({
							method: "one_fm.one_fm.page.ows.ows.get_okr_details",
							args: {
								okr_year: me.okr_year,
								okr_quarter: me.okr_quarter
							},
							callback: function(r) {
								if (r.message){
									let data = r.message;
									me.company_goal =  data.company_goal;
									me.company_objective =  data.company_objective ? data.company_objective.name : '';
									me.company_objective_quarter =  data.company_objective_quarter ? data.company_objective_quarter.name : '';
									me.my_objective =  data.my_objective ? data.my_objective.name : '';
								}
							}
						});
					},
					setupTriggers(){
						let me = this

						$('#okr_year').change(function(){
							me.fetchOKR();
							if(me.okr_year){
								$('#okr_quarter').prop('disabled', false);
							}
							else{
								$('#okr_quarter').prop('disabled', 'disabled');
								$("#okr_quarter").val("Default");
							}
						})

						$('#okr_quarter').change(function(){
							me.fetchOKR()
						})

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
									me.company_goal =  res.company_goal;
									me.company_objective =  res.company_objective ? res.company_objective.name : '';
									me.company_objective_quarter =  res.company_objective_quarter ? res.company_objective_quarter.name : '';
									me.my_objective =  res.my_objective ? res.my_objective.name : '';
									me.my_todos = res.my_todos;
									me.assigned_todos = res.assigned_todos;
									me.scrum_projects = res.scrum_projects;
									me.personal_projects = res.personal_projects;
									me.active_repetitive_projects = res.active_repetitive_projects;
									me.doctype_ref = res.filter_references[0];
									me.user_ref = res.filter_references[1];
									me.routine_tasks = res.routine_tasks;

									if(res.reset_filters == 1){
										me.setupFilters(1)
										me.setupFilters(0)
									}

									me.setOKRYearQuarter(res.okr_year)
								}
							}
						});
					},
					setOKRYearQuarter(okr_year_data){
						$('#okr_year').empty()
						$('#okr_year').select2({
							data:[{ 'id': '', 'text': 'Default' }].concat(okr_year_data)
						})

						$('#okr_quarter').empty()
						$('#okr_quarter').select2({
							data:[
								{ 'id': '', 'text': 'Default' },
								{ 'id': 'Q1', 'text': 'Q1' },
								{ 'id': 'Q2', 'text': 'Q2' },
								{ 'id': 'Q3', 'text': 'Q3' },
								{ 'id': 'Q4', 'text': 'Q4' },
							]
						})
						$('#okr_quarter').prop('disabled', 'disabled');
					},
					showTodo(todoType, todoName){
						// 1 = mytodo, 0 = assigned_todo
						let me = this;
						let todo = me.all_todos.filter(function(item){
							return item.name==todoName;
						});
						if (todo.length>0){
							me.todo_pane = todo[0];
							me.todo_pane.url = frappe.urllib.get_base_url()+'/app/todo/'+me.todo_pane.name
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
