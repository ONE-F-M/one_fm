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
		frm.set_query("post", "assignments", function() {
			return {
				query: "one_fm.operations.doctype.post_allocation_plan.post_allocation_plan.filter_posts",
				filters: {operations_shift, date}
			}
		});
	} else if(operations_shift != undefined && date == undefined){
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

			//PRIORITY 2
			employees = posts[2] && assign_post(frm, posts[2], employees);
			//PRIORITY 1
			employees = posts[1] && assign_post(frm, posts[1], employees);
			//PRIORITY 0
			employees = posts[0] && assign_post(frm, posts[0], employees);
		
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

function assign_post(frm, posts, employees){
	posts.forEach(function(i,v){
		let {designations} = posts[v];

		// Select matching designations employees only and pass to get_best_employee_match
		let matching_employees = employees.filter(emp => designations.includes(emp.designation))
		let match = get_best_employee_match(posts[v], matching_employees);

		frm.add_child('assignments', {
			employee: match.employee ? match.employee : undefined,
			employee_name: match.employee ? match.employee_name : undefined,
			post: posts[v] ? posts[v].post : undefined 
		}); 
		if(match.employee){
			employees = employees.filter(x => x.employee !== match.employee)
		}
	})
	return employees;
}

function get_best_employee_match(post, employees){
	// Create score based by summing up every (Employee Skill/Post Skill) and sorting based on the score.
	let scores = [];
	let {skills, designations, gender} = post;

	employees.forEach(function(employee,i){
		let skill_score = 0;
		skills.forEach(function(skill, i){
			employee.skills.forEach(function(e_skill, i){
				if(skill.skill == e_skill.skill){
					skill_score += roundNumber(e_skill.proficiency/ skill.proficiency, 2)
				}
			})
		})

		let gender_score = 0;
		//Increase if gender matches
		if(gender == "Both"){
			scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score + gender_score});
		}
		else if(gender == "Male" && employee.gender == "Male"){
			scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score + gender_score});
		}
		else if(gender == "Female" && employee.gender == "Female"){
			scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score + gender_score});
		}

	})
	//Sort descending by score 
	scores.sort((a, b) => (a.final_score < b.final_score) ? 1 : -1)

	let match = scores.length > 0 ? scores[0] : {'employee': undefined, 'score': 0};
	return match;
}
