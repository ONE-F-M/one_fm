// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Indemnity', {
	employee: function(frm) {
		set_indemnity_for_employee(frm);
	},
	date_of_joining: function(frm) {
		set_indemnity_for_employee(frm);
	},
	exit_date: function(frm) {
		set_indemnity_for_employee(frm);
	},
	exit_status: function(frm) {
		set_indemnity_for_employee(frm);
	}
});

var set_indemnity_for_employee = function(frm) {
	if(frm.doc.employee && frm.doc.date_of_joining && frm.doc.exit_date && frm.doc.exit_status){
		frappe.call({
			method: 'one_fm.one_fm.doctype.employee_indemnity.employee_indemnity.get_indemnity_for_employee',
			args: {'employee': frm.doc.employee, 'exit_status': frm.doc.exit_status, 'doj': frm.doc.date_of_joining, 'exit_date': frm.doc.exit_date},
			callback: function(r) {
				if(r && r.message){
					var data = r.message;
					var per_day_amount = frm.doc.basic_salary/30;
					frm.set_value('indemnity_allocation', data.allocation);
					frm.set_value('indemnity_policy', data.policy);
					frm.set_value('indemnity_percentage', data.indemnity_percentage);
					frm.set_value('total_indemnity_days_allowed', data.total_indemnity_allowed);
					frm.set_value('indemnity_amount', per_day_amount * data.total_indemnity_allowed);
				}
			}
		});
	}
};
