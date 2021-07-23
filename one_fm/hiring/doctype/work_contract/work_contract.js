// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Contract', {
	employee: function(frm) {
		set_employee_details(frm);
	},
	onboard_employee: function(frm) {
		set_employee_details(frm);
	}
});

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
