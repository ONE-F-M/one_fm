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
			let {employees, posts} = res;
			frm.set_value('assignments', '');

			posts.forEach(function(i,v){
				let match = get_best_employee_match(posts[v], employees)
				frm.add_child('assignments', {
					employee: match.employee ? match.employee : undefined,
					employee_name: match.employee ? match.employee_name : undefined,
					post: posts[v] ? posts[v].post : undefined 
				});
				if(match.employee){
					employees = employees.filter(x => x.employee !== match.employee)
				}
			})
			console.log(employees);
			if(employees.length > 0){
				employees.forEach(function(i,v){
					frm.add_child('assignments', {
						employee: employees[v] ? employees[v].employee : undefined,
						employee_name: employees[v].employee ? employees[v].employee_name : undefined,
					});
				});
			}
			frm.refresh_field("assignments");
		})
	}
}

function get_best_employee_match(post, employees){
	console.log(post);
	console.log(employees);
	let scores = [];
	// let score = 0;
	let {skills, designations, gender} = post;

	employees.forEach(function(i,v){
		let employee = employees[v];
		//Increase score if designation matches
		let designation_score = designations.includes(employees[v].designation) ? 1 : 0;

		// Increase if skill match 
		let post_skill_list = skills.map(a => a.skill);
		let employee_skill_list = employee.skills.map(a => a.skill);
		let skill_score = employee_skill_list.every(val => post_skill_list.includes(val)) ? 1 : 0;
		let gender_score = 0;
		//Increase if gender matches
		if(gender == "Both"){
			gender_score = 1;
		}
		else if(gender == "Male" && employee.gender == "Male"){
			gender_score = 1;
		}
		else if(gender == "Female" && employee.gender == "Female"){
			gender_score = 1;
		}

		if(designation_score && gender_score && skill_score){
			scores.push({'employee': employee.employee, 'employee_name': employee.employee_name});
		}
	})
	//Sort descending by score 
	scores.sort((a, b) => (a.employee_name < b.employee_name) ? 1 : -1)
	console.log(scores);

	let match = scores.length > 0 ? scores[0] : {'employee': undefined, 'score': 0};
	return match;
}

function get_best_post_match(employee, posts){
	console.log(posts);
	console.log(employee);

}