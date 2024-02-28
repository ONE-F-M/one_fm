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
						okr_quarter: '',
						timer: null
					}
				},
				mounted(){
					// show page content
					this.setupJS();
					this.getDefault();
					this.setupTriggers()
					this.timer = setInterval(() => {
						this.refresh()
					}, 60000) //Refresh every one minute
				},
				methods: {
					refresh(){
						console.log("Refreshing.....")
						this.getDefault()						
					  },
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
					setupFilters(is_my_todo,result_set){
						let me = this;
						let my_todo_user_data = [{ 'id': '', 'text': 'Select Assigned' }]
						let my_todo_reference_data = [{ 'id': '', 'text': 'Select Reference' }]
						let my_todo_priority_data = [{ 'id': '', 'text': 'Select Priority' }]
						let assigned_todo_user_data = [{ 'id': '', 'text': 'Select Allocated' }]
						let assigned_todo_reference_data = [{ 'id': '', 'text': 'Select Reference' }]
						let assigned_todo_priority_data = [{ 'id': '', 'text': 'Select Priority' }]
						let my_assigned_refname = []
						let my_todo_refname = []
						let my_assigned_priority = []
						let my_todo_priority = []
						let my_assigned_user = []
						let my_todo_user = []
						
						
						if(is_my_todo){
							result_set.my_todo_filters.forEach((obj) => {
								if(!my_todo_refname.includes(obj.reference_type)){
									
									my_todo_reference_data.push({
										'id':obj.reference_type,'text':obj.reference_type
									})
									my_todo_refname.push(obj.reference_type)
								}
								if(!my_todo_priority.includes(obj.priority)){
									my_todo_priority_data.push({
										'id':obj.priority,'text':obj.priority
									})
									my_todo_priority.push(obj.priority)
	
								}
								if(!my_todo_user.includes(obj.assigned_by)){
									
									my_todo_user_data.push({
										'id':obj.assigned_by,'text':obj.assigned_by
									})
									my_todo_user.push(obj.assigned_by)
	
								}
							})
							$('#my_todos_ref_type').empty()
							$('#my_todos_assigned_by').empty()
							$('#my_todos_priority').empty()
							
							$('#my_todos_ref_type').select2({
								data:my_todo_reference_data,
								width:'100%'
							})
							$('#my_todos_assigned_by').select2({
								data:my_todo_user_data,
								width:'100%'
							})
							$('#my_todos_priority').select2({
								data:my_todo_priority_data,
								width:'100%'
							})
						}
						else{
							result_set.assigned_todo_filters.forEach((obj) => {
								if(!my_assigned_refname.includes(obj.reference_type)){
									assigned_todo_reference_data.push({
										'id':obj.reference_type,'text':obj.reference_type
									})
									my_assigned_refname.push(obj.reference_type)
	
								}
								if(!my_assigned_priority.includes(obj.priority)){
									assigned_todo_priority_data.push({
										'id':obj.priority,'text':obj.priority
									})
									my_assigned_priority.push(obj.priority)
	
								}
								if(!my_assigned_user.includes(obj.allocated_to)){
									assigned_todo_user_data.push({
										'id':obj.allocated_to,'text':obj.allocated_to
									})
									my_assigned_user.push(obj.allocated_to)
	
								}
							})
							$('#assigned_reference_type').empty()
							$('#assigned_to').empty()
							$('#assigned_priority').empty()

							$('#assigned_reference_type').select2({
								data:assigned_todo_reference_data,
								width:'100%'
							})
							$('#assigned_to').select2({
								data:assigned_todo_user_data,
								width:'100%'
							})
							$('#assigned_priority').select2({
								data:assigned_todo_priority_data,
								width:'100%'
							})
						}
					},
					getDefault(){
						let me = this;
						me.hide_show_button()
						frappe.call({
							method: "one_fm.one_fm.page.ows.ows.get_defaults",
							args: {
								args :[me.my_todo_filters,me.assigned_todo_filters] || [],
								has_todo_filter : Object.keys(me.my_todo_filters).length,
								has_assigned_filter : Object.keys(me.assigned_todo_filters).length
							},
							callback: function(r) {
	
								if (r.message){
									me.loadSpinner(0)
									let res = r.message;
									me.company_goal =  res.company_goal;
									me.company_objective =  res.company_objective ? res.company_objective.name : '';
									me.company_objective_quarter =  res.company_objective_quarter ? res.company_objective_quarter.name : '';
									me.my_objective =  res.my_objective ? res.my_objective.name : '';
									me.all_todos = res.all_todos;
									me.my_todos = res.my_todos;
									me.assigned_todos = res.assigned_todos;
									me.scrum_projects = res.scrum_projects;
									me.personal_projects = res.personal_projects;
									me.active_repetitive_projects = res.active_repetitive_projects;
									me.doctype_ref = res.filter_references[0];
									me.user_ref = res.filter_references[1];
									me.routine_tasks = res.routine_tasks;

									if(res.reset_filters == 1){
										me.setupFilters(1,res)
										me.setupFilters(0,res)
									}

									me.setOKRYearQuarter(res.okr_year)
									$('#spinner-overlay').hide();
								}
							}
						});
					},
					clearTodo(){
						me = this
						me.todo_pane = {}
						me.hide_show_button()
						$('.todo-pane-block').hide();
					},
					editTodo(){
						$('#save_todo').show();
						$('#edit_todo_pane').hide();
						$("#status_field").prop('disabled', false);
						$("#description_field").prop('disabled', false);
						$("#priority_field").prop('disabled', false);
						// set color
						$('#status_field').prop('style', 'border: 3px solid blue;')
						$('#description_field').prop('style', 'border: 3px solid blue;')
						$('#priority_field').prop('style', 'border: 3px solid blue;')
					},
					saveTodo(){
						let me = this;
						// update todo
						frappe.call({
							url: `/api/resource/ToDo/${this.todo_pane.name}`,
							type: "PUT",
							args: {
								status:this.todo_pane.status,
								description: this.todo_pane.description,
								priority:this.todo_pane.priority
							},
							callback: function(r) {
								if (r.data){
									me.todo_pane = r.data;
									frappe.show_alert('ToDo update complete', 5);
									$('#save_todo').hide();
									$('#edit_todo_pane').show();
									$('#save_todo').hide();
									$("#status_field").prop('disabled', true);
									$("#description_field").prop('disabled', true);
									$("#priority_field").prop('disabled', true);
									// set color
									$('#status_field').prop('style', 'border: 1px solid black;')
									$('#description_field').prop('style', 'border: 1px solid black;')
									$('#priority_field').prop('style', 'border: 1px solid black;')
									me.getDefault();
									$('#clear_todo_pane').show();
									$('#copybutton').show()
									$('#gotobutton').show()
								} else {
									frappe.throw("An error occured, we could not update your ToDo.")
								}
							},
							always: function(r) {},
							freeze: true,
							freeze_message: "Updating ToDO",
							async: true,
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
					showTodo(todoName){
						// 1 = mytodo, 0 = assigned_todo
						$('.todo-pane-block').show();
						$('#save_todo').hide();
						$('#edit_todo_pane').show();
						$('#save_todo').hide();
						$("#status_field").prop('disabled', true);
						$("#description_field").prop('disabled', true);
						$("#priority_field").prop('disabled', true);
						// set color
						$('#status_field').prop('style', 'border: 1px solid black;')
						$('#description_field').prop('style', 'border: 1px solid black;')
						$('#priority_field').prop('style', 'border: 1px solid black;')
						let me = this;
						me.hide_show_button(1)
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
							$('#spinner').hide();
							$('#app-container').show();
						} else {
							$('#spinner').show();
							$('#app-container').hide();
						}

					},
					setupJS(){
						me = this
						var $input = $('<a class="btn btn-default icon-btn text-center" @click="refresh" id="refresh">&#x21bb;</a>');
   						$input.appendTo($(".page-head-content"));
						$input.on('click', function() {
							// Your refresh logic here
							$('#spinner-overlay').show();
							$('#spinner').show();
							me.refresh();
							
						});
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
					open_ref(){
							window.open(`${window.location.origin}/app/todo/${this.todo_pane.name}`);
					},
					copyText() {
						if (navigator.clipboard && window.isSecureContext) {
							navigator.clipboard.writeText(`${window.location.origin}/app/todo/${this.todo_pane.name}`).then(()=>{
								frappe.show_alert({
									indicator: "green",
									message: __("Copied to clipboard."),
								});
							});
							
						}
					},
					hide_show_button(show=0){
						if(!show){
							$('#copybutton').hide()
							$('#gotobutton').hide()
							$('#clear_todo_pane').hide()
						}
						else{
							$('#copybutton').show()
							$('#gotobutton').show()
							$('#clear_todo_pane').show()
						}
						
					}
				},
				beforeDestroy() {
					clearInterval(this.timer)
				}
			}
		)
		app.mount('#OKR-APP')
	}, 5000)
}
