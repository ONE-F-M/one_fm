// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Checkin Issue', {
	employee: function(frm) {
		get_shift_assignment(frm);
	}
});

function get_shift_assignment(frm){
	if(frm.doc.employee){
		frappe.call({
			method: 'one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue.fetch_approver',
			args:{
				'employee':frm.doc.employee
			},
			callback: function(r) {
				let val = r.message
				let assigned_shift, shift_supervisor, shift, shift_type = "";
				if(val && val.includes(null) != true){
					[assigned_shift, shift_supervisor, shift, shift_type] = r.message;
				}
				else{
					frappe.msgprint(__(`No shift assigned to ${frm.doc.employee_name}. Please check again.`));
				}
				frappe.model.set_value(frm.doctype, frm.docname, "assigned_shift", assigned_shift);
				frappe.model.set_value(frm.doctype, frm.docname, "shift_supervisor", shift_supervisor);
				frappe.model.set_value(frm.doctype, frm.docname, "shift", shift);
				frappe.model.set_value(frm.doctype, frm.docname, "shift_type", shift_type);
				frm.refresh_fields();
			}
		});
	}
};
