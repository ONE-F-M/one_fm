// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Post Allocation Plan', {
	refresh: function(frm){
		frm.add_fetch("employee", "employee_name", "employee_name");
		frm.add_fetch("employee", "employee_id", "employee_id");
		render_day_off_table(frm);
		render_prev_day_off_table(frm);
	},
	operations_shift: function(frm) {
		apply_post_allocation_filters(frm);
		add_employees(frm);
		render_day_off_table(frm);
		render_prev_day_off_table(frm);
	},
	date: function(frm) {
		apply_post_allocation_filters(frm);
		add_employees(frm);
		render_day_off_table(frm);
		render_prev_day_off_table(frm);
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

			// Fill posts in decreasing priority level. e.g Level 10 first, Level 9 then......Level 1 at the end
			for(let i=10; i>=1; i--){
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
		let matching_employees = employees.filter(emp => designations.includes(emp.designation));

		let match = get_best_employee_match(posts[v], matching_employees);

		frm.add_child('assignments', {
			employee: match.employee ? match.employee : undefined,
			employee_name: match.employee ? match.employee_name : undefined,
			post: posts[v] ? posts[v].post : undefined, 
			match_percentage: match.employee ? match.match_percentage : "0%" ,
			skill_score: match.employee ? match.score_details : undefined
		}); 

		if(match.employee){
			employees = employees.filter(x => x.employee !== match.employee)
		}
	})
	return employees;
}

//Returns list of certifications that have not expired
function get_valid_employee_certifications(employee){
	let result = [];
	employee.certifications.forEach(function(certification,i){
		let date = new Date();
		let today = date.toISOString().slice(0,10);
		let modified_today = new Date(today);
		let expiry_date = new Date(certification.expiry_date);
		if(modified_today < expiry_date){
			result.push(certification.certification);
		}
	})

	return result;
}

//This function returns list of licenses that have not expired
function get_valid_employee_licenses(employee){
	let result = [];
	employee.licenses.forEach(function(license,i){
		let date = new Date();
		let today = date.toISOString().slice(0,10);
		let modified_today = new Date(today);
		let expiry_date = new Date(license.expiry_date);
		if(modified_today < expiry_date){
			result.push(license.license);
		}
	})

	return result;
}

function get_best_employee_match(post, employees){
	// Create score based by summing up every (Employee Skill/Post Skill) and sorting based on the score.
	let scores = [];
	let {skills, designations, gender, certifications, licenses} = post;

	employees.forEach(function(employee,i){
		let skill_score = 0;
		let certification_match = 1;
		let license_match = 1;

		// Check if all the employee skills are matching the post skills.
		let post_skill_list = skills.map(a => a.skill);
		let employee_skill_list = employee.skills.map(a => a.skill);
		let skill_match = post_skill_list.every(val => employee_skill_list.includes(val)) ? 1 : 0;

		//If post has certifications, check if employee has the post certifications
		if(certifications.length > 0){
			let employee_certification_list = get_valid_employee_certifications(employee);
			certification_match = employee_certification_list.some(val => certifications.includes(val)) ? 1 : 0;
		}
		//If post has licenses, check if employee has the post licenses
		if(licenses.length > 0){
			let employee_license_list = get_valid_employee_licenses(employee);
			license_match = employee_license_list.some(val => licenses.includes(val)) ? 1 : 0;
		}	

		// If all skills match, calculate the skill score
		if(skill_match && certification_match && license_match){
			let score_detail = ``;
			let skill_length = 0;
			skills.forEach(function(skill, i){
				employee.skills.forEach(function(e_skill, i){
					if(skill.skill == e_skill.skill){
						skill_length++;
						skill_score += roundNumber(e_skill.proficiency/ skill.proficiency, 2)
						score_detail += `${skill.skill} : ${e_skill.proficiency}/${skill.proficiency}<br>`;
					}
				})
			})

			//Match percentage
			let match_percent = roundNumber((skill_score * 100) / skill_length);

			// 
			let rotation_check = true;
			let day_off_check = true;
			if(post.allow_staff_rotation){
				if(post.post.includes("Supervisor")){
					rotation_check = (post.post == employee.previous_day_schedule) && (post.post == employee.day_before_previous_day_schedule) ? false : true;
				} else {
					rotation_check = post.post == employee.previous_day_schedule ? false : true;
				}
				if(post.day_off_priority && employee.previous_day != "Day Off"){
					day_off_check = false;
				}
			}
			//Push the score to list if gender matches
			if(gender == "Both" && rotation_check && day_off_check){
				scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score, 'score_details': score_detail, 'match_percentage': `${match_percent}%`});
			}
			else if(gender == "Male" && employee.gender == "Male" && rotation_check && day_off_check){
				scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score, 'score_details': score_detail, 'match_percentage': `${match_percent}%`});
			}
			else if(gender == "Female" && employee.gender == "Female" && rotation_check && day_off_check){
				scores.push({'employee': employee.employee, 'employee_name': employee.employee_name, 'final_score': skill_score, 'score_details': score_detail, 'match_percentage': `${match_percent}%`});
			}
		}

	})
	//Sort descending by score and return best match
	scores.sort((a, b) => (a.final_score < b.final_score) ? 1 : -1)

	let match = scores.length > 0 ? scores[0] : {'employee': undefined, 'score': 0};
	return match;
}


frappe.ui.form.on('Post Allocation Employee Assignment', {
	employee: function(frm, cdt, cdn){
		let doc = locals[cdt][cdn];
		if(doc.employee == undefined){
			frappe.model.set_value("Post Allocation Employee Assignment", doc.name, "employee_name", undefined);
			frappe.model.set_value("Post Allocation Employee Assignment", doc.name, "skill_score", undefined);
			frappe.model.set_value("Post Allocation Employee Assignment", doc.name, "match_percentage", undefined);
		}
		else{
			let {employee, post, operations_shift, date} = doc;
			frappe.xcall('one_fm.operations.doctype.post_allocation_plan.post_allocation_plan.get_post_employee_data', {employee, post, operations_shift, date}).then(res => {
				let {employee, post} = res;
				let match = get_best_employee_match(post, [employee]);
				if(match){
					frappe.model.set_value("Post Allocation Employee Assignment", doc.name, "match_percentage", match.match_percentage);
					frappe.model.set_value("Post Allocation Employee Assignment", doc.name, "skill_score", match.score_details);
				} else {
					frappe.throw(__("Employee doesn't match the Post criteria."))
				}
			})
		}
	}
});


function render_day_off_table(frm){
	let {operations_shift, date} = frm.doc;
	if(operations_shift != undefined && date != undefined){
		date = moment(date).subtract(1, 'days').format('YYYY-MM-DD');
		frappe.xcall('one_fm.operations.doctype.post_allocation_plan.post_allocation_plan.get_day_off_employees', {operations_shift, date})
		.then(employees => {
			let wrapper = frm.fields_dict["yesterday_dayoff"].$wrapper;

			wrapper.empty().append(`
			<div class="container">
				<h2>Employees on Day Off on ${moment(date).format("DD-MM-YYYY")}</h2>            
				<table class="table table-bordered">
					<thead>
						<tr>
						<th>Employee</th>
						<th>Employee Name</th>
						<th>Designation</th>
						</tr>
					</thead>
					<tbody id="post-allocation-day-off">
					</tbody>
				</table>
			</div>
			`);

			let $tbody = $('#post-allocation-day-off');
			employees.forEach(function(employee,i){
				$tbody.append(`
				<tr>
					<td>${employee.name}</td>
					<td>${employee.employee_name}</td>
					<td>${employee.designation}</td>
			  	</tr>`)
			});
		})
	}
}

function render_prev_day_off_table(frm){
	let {operations_shift, date} = frm.doc;
	if(operations_shift != undefined && date != undefined){
		frappe.xcall('one_fm.operations.doctype.post_allocation_plan.post_allocation_plan.get_day_off_employees', {operations_shift, date})
		.then(employees => {
			let wrapper = frm.fields_dict["today_dayoff"].$wrapper;

			wrapper.empty().append(`
			<div class="container">
				<h2>Employees on Day Off on ${moment(date).format("DD-MM-YYYY")}</h2>            
				<table class="table table-bordered">
					<thead>
						<tr>
						<th>Employee</th>
						<th>Employee Name</th>
						<th>Designation</th>
						</tr>
					</thead>
					<tbody id="post-allocation-prev-day-off">
					</tbody>
				</table>
			</div>
			`);

			let $tbody = $('#post-allocation-prev-day-off');
			employees.forEach(function(employee,i){
				$tbody.append(`
				<tr>
					<td>${employee.name}</td>
					<td>${employee.employee_name}</td>
					<td>${employee.designation}</td>
			  	</tr>`)
			});
		})
	}
}