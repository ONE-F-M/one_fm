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

			// Fill posts in decreasing priority level. e.g Level 5 first, Level 4 then......Level 1 at the end
			for(let i=5; i>=1; i--){
				employees = (posts[i] && assign_post(frm, posts[i], employees)) || employees;
			}

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
			post: posts[v] ? posts[v].post : undefined, 
			skill_score: match.employee ? match.score_details : undefined
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

		// Check if all the employee skills are matching the post skills.
		let post_skill_list = skills.map(a => a.skill);
		let employee_skill_list = employee.skills.map(a => a.skill);
		let skill_match = employee_skill_list.every(val => post_skill_list.includes(val)) ? 1 : 0;

		// If all skills match, calculate the skill score
		if(skill_match){
			let score_detail = ``;
			skills.forEach(function(skill, i){
				employee.skills.forEach(function(e_skill, i){
					if(skill.skill == e_skill.skill){
						skill_score += roundNumber(e_skill.proficiency/ skill.proficiency, 2)
						score_detail += `${skill.skill} : ${e_skill.proficiency}/${skill.proficiency}<br>`;
					}
				})
			})
			console.log(score_detail);
			//Push the score to list if gender matches
			if(gender == "Both"){
				scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score, 'score_details': score_detail});
			}
			else if(gender == "Male" && employee.gender == "Male"){
				scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score, 'score_details': score_detail});
			}
			else if(gender == "Female" && employee.gender == "Female"){
				scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score, 'score_details': score_detail});
			}
		}

	})
	//Sort descending by score and return best match
	scores.sort((a, b) => (a.final_score < b.final_score) ? 1 : -1)

	let match = scores.length > 0 ? scores[0] : {'employee': undefined, 'score': 0};
	console.log(match)
	return match;
}
