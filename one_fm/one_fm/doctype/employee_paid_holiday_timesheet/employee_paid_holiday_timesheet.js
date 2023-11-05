// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Paid Holiday Timesheet', {
	approver: function(frm) {
		if(frm.doc.approver){
			frm.set_value("approver_name", frappe.user.full_name(frm.doc.approver));
		}
	}
});
