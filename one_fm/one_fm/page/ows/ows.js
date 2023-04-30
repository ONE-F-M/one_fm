frappe.require([
	'/assets/one_fm/js/vue.global.js',
	// '/assets/one_fm/js/datepicker.min.js',
	'/assets/one_fm/css/okr/okr.css'
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
					getDefault(){
						let me = this;
						frappe.call({
							method: "one_fm.one_fm.page.ows.ows.get_defaults", //dotted path to server method
							callback: function(r) {
								// code snippet
								console.log(r.message);
								if (r.message){
									let res = r.message;
									me.my_todos = res.my_todos;
									me.assigned_todos = res.assigned_todos;
									me.scrum_projects = res.scrum_projects;
									me.personal_projects = res.personal_projects;
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
					  	}).datepicker('update', new Date());
					}
				}
			}
		)
		app.mount('#OKR-APP')
	}, 5000)
}
