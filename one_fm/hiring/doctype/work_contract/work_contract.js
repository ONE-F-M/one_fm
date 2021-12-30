// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Contract', {
	refresh(frm) {
        // if reference_type and reference_name are set,
        // add a custom button to go to the reference form
        populate_autorized_signatory(frm)
		//frm.set_df_property('posting_date', 'read_only', 0);

    },
	employee: function(frm) {
		set_employee_details(frm);
	},
	onboard_employee: function(frm) {
		set_employee_details(frm);
	}
});

var populate_autorized_signatory = function(frm) {
	frappe.call({
		doc: frm.doc,
		method: 'get_authorized_signatory',
			callback: function(r) {
			if(r && r.message){
				frm.set_df_property('select_authorised_signatory_signed_work_contract', 'options', r.message);
			}
		}
	});
};

var set_employee_details = function(frm) {
	frappe.call({
		method: 'one_fm.hiring.doctype.work_contract.work_contract.get_employee_details_for_wc',
		args: {'type': frm.doc.type, 'employee': frm.doc.employee, 'onboard_employee': frm.doc.onboard_employee},
		callback: function(r) {
			if(r && r.message){
				var data = r.message;
				frm.set_value('employee_name', data.employee_name);
				frm.set_value('employee_name_in_arabic', data.employee_name_in_arabic);
				frm.set_value('nationality', data.nationality);
				frm.set_value('civil_id', data.civil_id);
				frm.set_value('passport_number', data.passport_number);
				frm.set_value('designation', data.designation);
				frm.set_value('monthly_salary', data.monthly_salary);
				frm.set_value('working_hours', data.working_hours);
				frm.set_value('effective_from', data.effective_from);
			}
		}
	});
};
