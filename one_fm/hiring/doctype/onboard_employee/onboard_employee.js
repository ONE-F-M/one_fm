// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Onboard Employee', {
	refresh: function(frm) {
		set_progress_html(frm);
		if (frm.doc.employee) {
			frm.add_custom_button(__('Employee'), function() {
				frappe.set_route("Form", "Employee", frm.doc.employee);
			},__("View"));
		}
		set_filters(frm);
		create_custom_buttons(frm);
	},
	is_g2g_fees_needed: function(frm) {
		if(!frm.doc.is_g2g_fees_needed){
			frm.set_value('g2g_fee_amount', 0);
		}
	},
	is_residency_fine_needed: function(frm) {
		if(!frm.doc.is_residency_fine_needed){
			frm.set_value('residency_fine_amount', 0);
		}
	},
	g2g_fee_amount: function(frm) {
		calculate_g2g_and_residency_total(frm);
	},
	residency_fine_amount: function(frm) {
		calculate_g2g_and_residency_total(frm);
	},
	applicant_agree_to_pay_the_amount: function(frm) {
		if(frm.doc.applicant_agree_to_pay_the_amount == 'Yes'){
			frm.set_value('down_payment_amount', frm.doc.total_g2g_residency_amount);
		}
		else{
			frm.set_value('down_payment_amount', 0);
		}
	},
	down_payment_amount: function(frm) {
		if(frm.doc.down_payment_amount && frm.doc.down_payment_amount > 0){
			frm.set_value('net_loan_amount', frm.doc.total_g2g_residency_amount - frm.doc.down_payment_amount);
		}
		else{
			frm.set_value('net_loan_amount', frm.doc.down_payment_amount);
		}
	},
	update_document_and_create_payment_request: function(frm) {
		var freaze_msg = '';
		if(frm.doc.is_g2g_fees_needed){
			freaze_msg += " G2G"
		}
		if(frm.doc.is_residency_fine_needed){
			freaze_msg += " Residency Fine"
		}
		frappe.call({
			doc: frm.doc,
			method: "create_g2g_residency_payment_request",
			callback: function(r) {
				if(!r.exc){
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: __("Creating Payment Request -{0} !!", [freaze_msg])
		});
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
	},
	btn_create_bank_account: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'create_bank_account',
			callback: function(r) {
				if(!r.exc){
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: (__('Creating Bank Account ....!'))
		});
	},
	btn_create_erpnext_user: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'create_user_and_permissions',
			callback: function(r) {
				if(!r.exc){
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: (__('Creating ERPNext User ....!'))
		});
	},
	btn_create_loan: function(frm) {
		btn_create_loan_action(frm);
	}
});

var calculate_g2g_and_residency_total = function(frm) {
	var g2g_fee_amount = 0;
	var residency_fine_amount = 0;
	if(frm.doc.g2g_fee_amount && frm.doc.g2g_fee_amount > 0){
		g2g_fee_amount = frm.doc.g2g_fee_amount;
	}
	if(frm.doc.residency_fine_amount && frm.doc.residency_fine_amount > 0){
		residency_fine_amount = frm.doc.residency_fine_amount;
	}
	frm.set_value('total_g2g_residency_amount', g2g_fee_amount+residency_fine_amount);
};

var set_filters = function(frm) {
	frm.set_query('leave_policy', function() {
		return {
			filters: {
				"docstatus": 1
			}
		};
	});
};

var create_custom_buttons = function(frm) {
	/*
		Button for creating the Work Contract, Declaration of Electronic Signature, Duty Commencement, Bank Account
		will comes in the below order asper the workflow in Onboard Employee
		1. Declaration of Electronic Signature - Create if Applicant Attended the Orientation
		2. Work Contract  - Create after the Declaration of Electronic Signature and electronic_signature_status should be True
		3. Duty Commencement - Create after Declaration of Electronic Signature
		4. Bank Account - Create only if Employee is Created and salary mode is Bank
	*/
	if(frm.doc.docstatus < 2){
		if(frm.doc.applicant_attended && !frm.doc.work_contract){
			cutom_btn_and_action(frm, 'create_work_contract', 'Work Contract');
		}
		if(frm.doc.work_contract_status == "Applicant Signed" && !frm.doc.duty_commencement){
			cutom_btn_and_action(frm, 'create_duty_commencement', 'Duty Commencement');
		}
		if(frm.doc.duty_commencement_status == "Applicant Signed and Uploaded" && !frm.doc.employee){
			cutom_btn_and_action(frm, 'create_employee', 'Employee');
		}
		if(frm.doc.employee && !frm.doc.employee_id){
			cutom_btn_and_action(frm, 'create_employee_id', 'Employee ID Card');
		}
		if(frm.doc.employee && !frm.doc.user_created){
			cutom_btn_and_action(frm, 'create_user_and_permissions', 'ERPNext User');
		}
		if(frm.doc.employee && frm.doc.user_created && !frm.doc.inform_and_send_enrolment_details_to_employee){
			frm.add_custom_button(__('Inform and Send Enrolment Details to Employee'), function() {
				frm.set_value('inform_and_send_enrolment_details_to_employee', true);
				frm.save("Update");
			}).addClass('btn-primary');
		}
		if(frm.doc.employee && !frm.doc.bank_account && frm.doc.salary_mode=='Bank'){
			cutom_btn_and_action(frm, 'create_bank_account', 'Bank Account');
		}
		if(frm.doc.employee && !frm.doc.loan && frm.doc.net_loan_amount > 0){
			frm.add_custom_button(__('Loan'), function() {
				btn_create_loan_action(frm);
			}, __('Create')).addClass('btn-primary');
		}
		if(frm.doc.employee && !frm.doc.mgrp && frm.doc.nationality == 'Kuwaiti'){
			cutom_btn_and_action(frm, 'create_mgrp', 'MGRP');
		}
		if(frm.doc.employee && !frm.doc.pifss_form_103 && frm.doc.nationality == 'Kuwaiti'){
			cutom_btn_and_action(frm, 'create_103_form', 'PIFSS Form 103');
		}
		if(frm.doc.employee && frm.doc.tools_needed_for_work && !frm.doc.request_for_material){
			cutom_btn_and_action(frm, 'create_rfm_from_eo', 'Request for Material');
		}
	}
};

var btn_create_loan_action = function(frm) {
	if(!frm.doc.loan_type){
		frappe.throw(__('Please select Loan Type !'));
	}
	else if(!frm.doc.repayment_method){
		frappe.throw(__('Please select Repayment Method !'))
	}
	else{
		frappe.call({
			doc: frm.doc,
			method: 'create_loan',
			callback: function(r) {
				if(!r.exc){
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: (__('Creating Loan ....!'))
		});
	}
};

var cutom_btn_and_action = function(frm, method, dt) {
	frm.add_custom_button(__(dt), function() {
		frappe.call({
			doc: frm.doc,
			method: method,
			callback: function(r) {
				if(!r.exc){
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: (__('Creating {0} ....!', [dt]))
		});
	}, __('Create')).addClass('btn-primary');
}

var set_offer_details = function(frm, job_offer) {
	var fields = ['employee_grade', 'job_applicant'];
	frm.set_value('date_of_joining', job_offer.estimated_date_of_joining)
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
		'passport_type', 'visa_type', 'civil_id', 'cid_expire', 'is_uniform_needed_for_this_job', 'shoulder_width',
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

var set_progress_html = function(frm) {
	var $wrapper = frm.fields_dict['progress_html'].$wrapper;
	var selected = 'btn-primary';

	var work_contract = 'work_contract';
	var field_html = `<div class="row"><div class="col-sm-12">`
	field_html += get_progress_details(frm, 'Orientation', frm.doc.candidate_orientation_progress || 0, frm.doc.candidate_orientation_docstatus || 0);
	field_html += get_progress_details(frm, 'Work Contract', frm.doc.work_contract_progress || 0, frm.doc.work_contract_docstatus || 0);
	field_html += get_progress_details(frm, 'Duty Commencement', frm.doc.duty_commencement_progress || 0, frm.doc.duty_commencement_docstatus || 0);
	field_html += get_progress_details(frm, 'Bank Account', frm.doc.bank_account_progress || 0, frm.doc.bank_account_docstatus || 0);
	field_html += get_progress_details(frm, 'Accommodation', 0, 0);
	field_html += get_progress_details(frm, 'Transportation', 0, 0);
	field_html += get_progress_details(frm, 'Assets for Work', 0, 0);
	field_html += get_progress_details(frm, 'Employee ID', frm.doc.employee_id_progress || 0, frm.doc.employee_id_docstatus || 0);
	field_html += get_progress_details(frm, 'Transfer Paper', 0, 0);
	field_html += `</div>`
	var progress = 35
	var progress_bgc = 'blue';
	field_html += `<hr/><div class="row">
		<div class="col-sm-12">
			<div class="col-sm-2 small">Onboarding</div>
			<div class="col-sm-10">
				<div class="progress level" style="margin: 3px;">
					<div class="progress-bar progress-bar-success" role="progressbar"
						aria-valuenow=${progress}
						aria-valuemin="0" aria-valuemax="100" style="width: ${progress}%; background-color: ${progress_bgc};">
					</div>
				</div>
			</div>
		</div>
	</div>`;
	$wrapper
		.html(field_html);
	// $wrapper.on('click', '.work_contract', function() {
	// 	if(frm.doc.docstatus == 0){
	// 		var $btn = $(this);
	// 		$wrapper.find('.work_contract').removeClass('btn-primary');
	// 		$btn.addClass('btn-primary');
	// 		console.log($btn.attr('data'));
	// 	}
	// });
};

var get_progress_details = function(frm, doctype, progress, docstatus) {
	var progress_bgc = '00FF00';
	progress_bgc = 'blue';
	if(docstatus == 1){
		progress_bgc = '00FF00';
	}
	if (docstatus == 2){
		progress_bgc = 'red';
	}
	return `<div class="col-sm-6"><div class="col-sm-5 small">
		${doctype}
	</div>
	<div class="col-sm-7">
		<div class="progress level" style="margin: 3px;">
			<div class="progress-bar progress-bar-success" role="progressbar"
				aria-valuenow=${progress}
				aria-valuemin="0" aria-valuemax="100" style="width: ${progress}%; background-color: ${progress_bgc};">
			</div>
		</div>
	</div></div>`
};