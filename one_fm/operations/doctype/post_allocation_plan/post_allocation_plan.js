// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Post Allocation Plan', {
	refresh: function(frm){
		frm.add_fetch("employee", "employee_name", "employee_name");
		frm.add_fetch("employee", "employee_id", "employee_id");
	},
	operations_shift: function(frm) {
		apply_post_allocation_filters(frm);
		add_employees(frm);
	},
	date: function(frm) {
		apply_post_allocation_filters(frm);
		add_employees(frm);
	}
});


function apply_post_allocation_filters(frm){
	let {operations_shift, date} = frm.doc;

	if(operations_shift != undefined && date != undefined){
		console.log(operations_shift, date);
		frm.set_query("post", "assignments", function() {
			return {
				query: "one_fm.operations.doctype.post_allocation_plan.post_allocation_plan.filter_posts",
				filters: {operations_shift, date}
			}
		});
	} else if(operations_shift != undefined && date == undefined){
		console.log(operations_shift, date);
		frm.set_query("post", "assignments", function() {
			return {
				"filters": [
					["Operations Post", "site_shift", "=", operations_shift],
				]
			}
		});
	}
}

function add_employees(frm){
	let {operations_shift, date} = frm.doc;

	if(operations_shift != undefined && date != undefined){
		frappe.xcall('one_fm.operations.doctype.post_allocation_plan.post_allocation_plan.get_table_data',{operations_shift, date})
		.then(res => {
			console.log(res);
			let {employees, posts} = res;
			let list = employees.length > posts.length ? employees : posts;
			console.log(list);
			frm.set_value('assignments', '');
			list.forEach(function(i,v){
				console.log(employees[v], posts[v]);
				frm.add_child('assignments', {
					employee: employees[v] ? employees[v].employee : undefined,
					employee_name: employees[v] ? employees[v].employee_name : undefined,
					post: posts[v] ? posts[v].name : undefined 
				});
			})
			frm.refresh_field("assignments");
		})
	}
}