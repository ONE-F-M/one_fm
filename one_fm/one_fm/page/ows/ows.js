frappe.require([
	'/assets/one_fm/js/vue.global.js',
	'/assets/one_fm/js/daterangepicker.min.js',
	'/assets/one_fm/js/roster_js/select2.min.js',
	'/assets/one_fm/css/okr/okr.css',
	'/assets/one_fm/css/okr/daterangepicker.css',
	
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
	console.log(wrapper)

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
						personal_projects: []
					}
				},
				mounted(){
					// show page content
					this.loadSpinner(0);
					this.setupJS();
					this.getDefault();
				},
				methods: {

					setupFilters(values,is_my_todo){
						let id_data = [{ 'id': '', 'text': 'Select ID' }]
						let assigned_data = [{ 'id': '', 'text': 'Select Assigned' }]
						let reference_data = [{ 'id': '', 'text': 'Select Reference' }]
						let priotity_data = [{ 'id': '', 'text': 'Select Priority' }]
						if(is_my_todo){
							id_arr=[]
							ref_arr = []
							assigned_arr = []
							priority_arr = []
							values.forEach((row)=>{
								if(!id_arr.includes(row.description.substring(0,70))){
									id_data.push({ 'id': row.name, 'text': row.description.substring(0,70) });
									id_arr.push(row.description.substring(0,70))
								}
								if(!ref_arr.includes(row.reference_type)){
									reference_data.push({ 'id': row.reference_type, 'text': row.reference_type })
									ref_arr.push(row.reference_type)
								}
								if(!assigned_arr.includes(row.assigned_by)){
									assigned_data.push({'id':row.assigned_by,'text':row.assigned_by})
									assigned_arr.push(row.assigned_by)
								}
								if(!priority_arr.includes(row.priority)){
									priotity_data.push({'id':row.priority,'text':row.priority})
									priority_arr.push(row.priority)
								}	
							})
							$('#my_todos_id').empty()
							$('#my_todos_ref_type').empty()
							$('#my_todos_assigned_by').empty()
							$('#my_todos_priority').empty()
							$('#my_todos_id').select2({
								data:id_data,
								width:'100%'
							})
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
							id_arr=[]
							ref_arr = []
							assigned_arr = []
							priority_arr = []
							values.forEach((row)=>{
								if(!id_arr.includes(row.description.substring(0,70))){
									id_data.push({ 'id': row.name, 'text': row.description.substring(0,70) });
									id_arr.push(row.description.substring(0,70))
								}
								if(!ref_arr.includes(row.reference_type)){
									reference_data.push({ 'id': row.reference_type, 'text': row.reference_type })
									ref_arr.push(row.reference_type)
								}
								if(!assigned_arr.includes(row.allocated_to)){
									assigned_data.push({'id':row.allocated_to,'text':row.allocated_to})
									assigned_arr.push(row.allocated_to)
								}
								if(!priority_arr.includes(row.priority)){
									priotity_data.push({'id':row.priority,'text':row.priority})
									priority_arr.push(row.priority)
								}	
							})
							$('#assigned_id').empty()
							$('#assigned_reference_type').empty()
							$('#assigned_to').empty()
							$('#assigned_priority').empty()
							$('#assigned_id').select2({
								data:id_data,
								width:'100%'
							})
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
							method: "one_fm.one_fm.page.ows.ows.get_defaults", //dotted path to server method
							callback: function(r) {
								// code snippet
								
								if (r.message){
									
									let res = r.message;
									me.my_todos = res.my_todos;
									me.assigned_todos = res.assigned_todos;
									me.scrum_projects = res.scrum_projects;
									me.personal_projects = res.personal_projects;
									me.setupFilters(me.my_todos,1)
									me.setupFilters(me.assigned_todos,0)
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
							}
						} else {
							let todo = me.assigned_todos.filter(function(item){
							return item.name==todoName;
							});
							if (todo.length>0){
								me.todo_pane = todo[0];
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
						$(".mydatepicker").datepicker({
							language:'en'
					  	}).datepicker('update', new Date());

						$('.date-range-picker').daterangepicker({
							autoUpdateInput: false,
							opens:'left',
							language:'en',
							locale: {
								format: 'DD-MM-YYYY'
							  },
							
							
						})
						$('.date-range-picker').on('apply.daterangepicker',(event,picker)=>{
							let me = this
							
							frappe.show_alert("SET DATE FILTER",5)
						})
					}
				}
			}
		)
		app.mount('#OKR-APP')
	}, 5000)
}
