// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('ERF', {
	refresh: function(frm) {
		frm.set_query('erf_request', function () {
			return {
				filters: {
					'docstatus': 1,
					'status': 'Accepted',
					'department_manager': frappe.user.name
				}
			};
		});
	},
	onload: function(frm) {
		set_other_benefits(frm);
	},
	total_no_of_candidates_required: function(frm) {
    calculate_total_cost_in_salary(frm);
    set_required_quantity_grd(frm);
	},
  salary_per_person: function(frm) {
    calculate_total_cost_in_salary(frm);
  },
  designation: function(frm) {
    set_basic_skill_from_designation(frm);
  },
	working_days: function(frm) {
		set_off_days(frm);
	},
	travel_required: function(frm) {
		manage_type_of_travel(frm);
	},
	driving_license_required: function(frm) {
		manage_type_of_license(frm);
	},
	grade: function(frm) {
		set_salary_structure(frm);
	},
	salary_structure: function(frm) {
		set_salary_details(frm);
	},
	erf_request: function(frm) {
		set_erf_request_details(frm);
	},
	status: function(frm) {
		set_reason_for_decline_reqd(frm);
	},
	performance_profile: function(frm) {
		set_objectives_and_krs(frm);
	},
	expected_date_of_deployment: function(frm) {
		validate_date(frm);
	}
});

var validate_date = function(frm) {
	if(frm.doc.expected_date_of_deployment < frm.doc.erf_initiation){
		frappe.throw(__("Expected Date of Deployment cannot be before ERF Initiation Date"));
	}
	if(frm.doc.expected_date_of_deployment < frappe.datetime.today()){
		frappe.throw(__("Expected Date of Deployment cannot be before Today"));
	}
};

frappe.ui.form.on('ERF Gender Height Requirement', {
	number: function(frm, cdt, cdn){
    calculate_total_required_candidates(frm, cdt, cdn);
  }
});

frappe.ui.form.on('ERF Salary Detail', {
	amount: function(frm, cdt, cdn){
    calculate_salary_per_person(frm);
  }
});

frappe.ui.form.on('ERF Employee Benefit', {
	cost: function(frm, cdt, cdn){
    calculate_benefit_cost_to_company(frm);
  }
});

var set_objectives_and_krs = function(frm) {
	frm.clear_table('objectives');
	frm.clear_table('key_results');
	if(frm.doc.performance_profile){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'OKR Performance Profile',
				filters: {name: frm.doc.performance_profile}
			},
			callback: function(r) {
				if(r && r.message){
					let objectives = r.message.objectives;
					objectives.forEach((item, i) => {
						let objective = frappe.model.add_child(frm.doc, 'OKR Performance Profile Objective', 'objectives');
						frappe.model.set_value(objective.doctype, objective.name, 'objective', item.objective);
						frappe.model.set_value(objective.doctype, objective.name, 'type', item.type);
						frappe.model.set_value(objective.doctype, objective.name, 'objective_linking_with', item.objective_linking_with);
						frappe.model.set_value(objective.doctype, objective.name, 'time_frame', item.time_frame);
					});
					let key_results = r.message.key_results;
					key_results.forEach((item, i) => {
						let kr = frappe.model.add_child(frm.doc, 'OKR Performance Profile Key Result', 'key_results');
						frappe.model.set_value(kr.doctype, kr.name, 'key_result', item.key_result);
						frappe.model.set_value(kr.doctype, kr.name, 'objective', item.objective);
						frappe.model.set_value(kr.doctype, kr.name, 'target_to_be_achieved_by', item.target_to_be_achieved_by);
					});
				}
				frm.refresh_field('objectives');
				frm.refresh_field('key_results');
			}
		});
	}
	else{
		frm.refresh_field('objectives');
		frm.refresh_field('key_results');
	}
};

var set_reason_for_decline_reqd = function(frm) {
	if(frm.doc.status == 'Declined'){
		frm.set_df_property('reason_for_decline', 'reqd', true);
	}
	else{
		frm.set_df_property('reason_for_decline', 'reqd', false);
	}
};

var set_erf_request_details = function(frm) {
	if(frm.doc.erf_request){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'ERF Request',
				filters: {name: frm.doc.erf_request}
			},
			callback: function(r) {
				if(r.message){
					let request = r.message
					frm.set_value('department', request.department);
					frm.set_value('designation', request.designation);
					frm.set_value('no_of_candidates_by_erf_request', request.number_of_candidates_required);
					frm.set_value('reason_for_request', request.reason_for_request);
				}
			}
		});
		frm.set_df_property('department', 'read_only', true);
		frm.set_df_property('designation', 'read_only', true);
		frm.set_df_property('reason_for_request', 'read_only', true);
	}
	else {
		frm.set_df_property('department', 'read_only', false);
		frm.set_df_property('designation', 'read_only', false);
		frm.set_df_property('reason_for_request', 'read_only', false);
	}
};

var calculate_benefit_cost_to_company = function(frm) {
	let total = 0;
	if(frm.doc.other_benefits){
    frm.doc.other_benefits.forEach(function(benefit) {
      total += benefit.cost;
    });
  }
  frm.set_value('benefit_cost_to_company', total);
	calculate_total_cost_to_company(frm);
};

var set_other_benefits = function(frm) {
	if(!frm.doc.other_benefits){
		frm.clear_table('other_benefits');
		let options = ['Company Provided Car', 'Mobile with Line', 'Health Insurance'];
		options.forEach((option) => {
			let benefit = frappe.model.add_child(frm.doc, 'ERF Employee Benefit', 'other_benefits');
			frappe.model.set_value(benefit.doctype, benefit.name, 'benefit', option);
		});
		frm.refresh_field('other_benefits');
	}
};

var set_salary_details = function(frm) {
	frm.clear_table('salary_details');
	if(frm.doc.salary_structure){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Salary Structure',
				filters: {name: frm.doc.salary_structure}
			},
			callback: function(r) {
				if(r.message && r.message.earnings){
					let earnings = r.message.earnings;
					earnings.forEach((earning) => {
						// TODO: Calculate formula values to the amount from salary Structure
						let salary_detail = frappe.model.add_child(frm.doc, 'ERF Salary Detail', 'salary_details');
        		frappe.model.set_value(salary_detail.doctype, salary_detail.name, 'salary_component', earning.salary_component);
        		frappe.model.set_value(salary_detail.doctype, salary_detail.name, 'amount', earning.amount);
					});
				}
				frm.refresh_field('salary_details');
			}
		});
	}
	frm.refresh_field('salary_details');
};

var set_salary_structure = function(frm) {
	if(frm.doc.grade){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Employee Grade',
				filters: {name: frm.doc.grade}
			},
			callback: function(r) {
					if(r.message && r.message.default_salary_structure){
						frm.set_value('salary_structure', r.message.default_salary_structure);
					}
					else{
						frm.set_value('salary_structure', '');
					}
			}
		});
	}
	else{
		frm.set_value('salary_structure', '');
	}
};

var manage_type_of_license = function(frm) {
	if(frm.doc.driving_license_required){
		frm.set_df_property('type_of_license', 'reqd', true);
	}
	else{
		frm.set_df_property('type_of_license', 'reqd', false);
		frm.set_value('type_of_license', '');
	}
};

var manage_type_of_travel = function(frm) {
	if(frm.doc.travel_required){
		frm.set_df_property('type_of_travel', 'reqd', true);
	}
	else{
		frm.set_df_property('type_of_travel', 'reqd', false);
		frm.set_value('type_of_travel', '');
	}
};

var set_off_days = function(frm) {
	if(frm.doc.working_days > 0){
		frm.set_value('off_days', 30-frm.doc.working_days);
	}
};

var set_required_quantity_grd = function(frm) {
  if(frm.doc.total_no_of_candidates_required){
    frm.set_value('required_quantity', frm.doc.total_no_of_candidates_required);
  }
  else{
    frm.set_value('required_quantity', 0);
  }
}

var calculate_total_required_candidates = function (frm, cdt, cdn) {
  let total = 0;
	var child = locals[cdt][cdn];
  if(frm.doc.gender_height_requirement){
    frm.doc.gender_height_requirement.forEach(function(required_candidate) {
      total += required_candidate.number;
    });
  }
	if(total > frm.doc.no_of_candidates_by_erf_request){
		frappe.model.set_value(child.doctype, child.name, 'number', 0);
		frm.refresh_field('gender_height_requirement');
		frappe.throw(__('Total Number Candidates Required Should not exceed ERF Request.'))
	}
  frm.set_value('total_no_of_candidates_required', total);
};

var calculate_salary_per_person = function (frm) {
  let total = 0;
  if(frm.doc.salary_details){
    frm.doc.salary_details.forEach(function(salary_detail) {
      total += salary_detail.amount;
    });
  }
  frm.set_value('salary_per_person', total);
};

var calculate_total_cost_in_salary = function (frm) {
  if(frm.doc.total_no_of_candidates_required > 0 && frm.doc.salary_per_person > 0){
    frm.set_value('total_cost_in_salary', frm.doc.total_no_of_candidates_required * frm.doc.salary_per_person);
  }
  else{
    frm.set_value('total_cost_in_salary', 0);
  }
	calculate_total_cost_to_company(frm);
};

var calculate_total_cost_to_company = function(frm) {
	if(frm.doc.total_cost_in_salary && frm.doc.benefit_cost_to_company){
		frm.set_value('total_cost_to_company', frm.doc.total_cost_in_salary+frm.doc.benefit_cost_to_company);
	}
};

var set_basic_skill_from_designation = function(frm) {
  frm.clear_table("designation_skill");
  if(frm.doc.designation){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: "Designation",
				filters: {"name":frm.doc.designation}
			},
			callback: function(r) {
				if(r.message && r.message.skills){
					let skills = r.message.skills;
					skills.forEach(function(designation_skill) {
						let skill = frappe.model.add_child(frm.doc, 'Designation Skill', 'designation_skill');
						frappe.model.set_value(skill.doctype, skill.name, 'skill', designation_skill.skill);
						frappe.model.set_value(skill.doctype, skill.name, 'one_fm_proficiency', designation_skill.one_fm_proficiency);
					});
				}
				frm.refresh_field('designation_skill');
			}
		});
  }
  frm.refresh_field('designation_skill');
};
