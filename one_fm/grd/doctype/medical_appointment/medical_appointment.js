// Copyright (c) 2025, one_fm and contributors
// For license information, please see license.txt

frappe.ui.form.on("Medical Appointment", {
	employee(frm) {
		frm.events.fetch_approver(frm);
	},
	fetch_approver(frm) {
		frm.set_value("employee_supervisor", null);
		if(frm.doc.employee){
			frappe.call({
				method: "one_fm.utils.get_employee_site_supervisor_user",
				args : {"employee": frm.doc.employee},
				callback: function (r) {
					if(r && r.message){
						frm.set_value("employee_supervisor", r.message);
					}
				}
			});
		}
	}
});
