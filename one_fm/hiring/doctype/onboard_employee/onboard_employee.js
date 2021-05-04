// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Onboard Employee', {
	setup: function(frm) {
		frm.add_fetch("employee_onboarding_template", "company", "company");
		frm.add_fetch("employee_onboarding_template", "department", "department");
		frm.add_fetch("employee_onboarding_template", "designation", "designation");
		frm.add_fetch("employee_onboarding_template", "employee_grade", "employee_grade");

		// frm.set_query('job_offer', function () {
		// 	return {
		// 		filters: {
		// 			'job_applicant': frm.doc.job_applicant
		// 		}
		// 	};
		// });
	},

	refresh: function(frm) {
		if (frm.doc.employee) {
			frm.add_custom_button(__('Employee'), function() {
				frappe.set_route("Form", "Employee", frm.doc.employee);
			},__("View"));
		}
		if (frm.doc.project) {
			frm.add_custom_button(__('Project'), function() {
				frappe.set_route("Form", "Project", frm.doc.project);
			},__("View"));
			frm.add_custom_button(__('Task'), function() {
				frappe.set_route('List', 'Task', {project: frm.doc.project});
			},__("View"));
		}
		if ((!frm.doc.employee) && (frm.doc.docstatus === 1)) {
			frm.add_custom_button(__('Employee'), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.hr.doctype.employee_onboarding.employee_onboarding.make_employee",
					frm: frm
				});
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
		if (frm.doc.docstatus === 1 && frm.doc.project) {
			frappe.call({
				method: "erpnext.hr.utils.get_boarding_status",
				args: {
					"project": frm.doc.project
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('boarding_status', r.message);
					}
					refresh_field("boarding_status");
				}
			});
		}

	},

	employee_onboarding_template: function(frm) {
		frm.set_value("activities" ,"");
		if (frm.doc.employee_onboarding_template) {
			frappe.call({
				method: "erpnext.hr.utils.get_onboarding_details",
				args: {
					"parent": frm.doc.employee_onboarding_template,
					"parenttype": "Employee Onboarding Template"
				},
				callback: function(r) {
					if (r.message) {
						r.message.forEach((d) => {
							frm.add_child("activities", d);
						});
						refresh_field("activities");
					}
				}
			});
		}
	},
	onboard_employee_template: function(frm) {
		frm.set_value("actions" ,"");
		if (frm.doc.onboard_employee_template) {
			frappe.call({
				method: "one_fm.hiring.utils.get_onboarding_details",
				args: {
					"parent": frm.doc.onboard_employee_template,
					"parenttype": "Onboard Employee Template"
				},
				callback: function(r) {
					if (r.message) {
						r.message.forEach((d) => {
							frm.add_child("actions", d);
						});
						refresh_field("actions");
					}
				}
			});
		}
	},
	job_applicant: function(frm) {
		frm.set_value("applicant_documents" ,"");
		if (frm.doc.job_applicant) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					"doctype": 'Job Applicant',
					"name": frm.doc.job_applicant
				},
				callback: function(r) {
					if(r.message){
						set_applicant_details(frm, r.message);
					}
				}
			});
		}
	},
	job_offer: function(frm) {
		if (frm.doc.job_offer) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					"doctype": 'Job Offer',
					"name": frm.doc.job_offer
				},
				callback: function(r) {
					if(r.message){
						set_offer_details(frm, r.message);
					}
				}
			});
		}
	}
});

var set_offer_details = function(frm, job_offer) {
	var fields = ['employee_grade', 'job_applicant'];
	fields.forEach((field, i) => {
		frm.set_value(field, job_offer[field]);
	});

	var one_fm_fields = ['salary_structure', 'job_offer_total_salary', 'provide_salary_advance', 'salary_advance_amount',
		'provide_accommodation_by_company', 'provide_transportation_by_company'];
	one_fm_fields.forEach((one_fm_field, i) => {
		frm.set_value(one_fm_field, job_offer['one_fm_'+one_fm_field]);
	});

	if (job_offer.one_fm_salary_details) {
		var data = job_offer.one_fm_salary_details;
		data.forEach((d) => {
			frm.add_child("salary_details", d);
		});
		refresh_field("salary_details");
	}
};

var set_applicant_details = function(frm, applicant) {
	var fields = ['email_id', 'department', 'project', 'source', 'nationality_no', 'nationality_subject',
		'date_of_naturalization'];
	fields.forEach((field, i) => {
		frm.set_value(field, applicant[field]);
	});

	var one_fm_fields = ['applicant_is_overseas_or_local', 'is_transferable', 'designation', 'agency', 'gender', 'religion',
	 	'date_of_birth', 'erf', 'height', 'place_of_birth', 'marital_status', 'nationality', 'contact_number',
		'secondary_contact_number', 'passport_number', 'passport_holder_of', 'passport_issued', 'passport_expire',
		'passport_type', 'visa_type', 'civil_id', 'cid_expire', 'uniform_needed_for_this_job', 'shoulder_width',
		'waist_size', 'shoe_size'];
	one_fm_fields.forEach((one_fm_field, i) => {
		frm.set_value(one_fm_field, applicant['one_fm_'+one_fm_field]);
	});

	if (applicant.one_fm_documents_required) {
		var data = applicant.one_fm_documents_required;
		data.forEach((d) => {
			frm.add_child("applicant_documents", d);
		});
		refresh_field("applicant_documents");
	}
	// frm.set_value('applicant_name', applicant.applicant_name);
};
