// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation", {
	refresh: function (frm) {
		if (!frm.doc.__islocal && frm.doc.docstatus < 2) {
			// Check if any withdrawal already exists
			frappe.db.count("Employee Resignation Withdrawal", {
				filters: {
					employee_resignation: frm.doc.name,
					docstatus: ["<", 2]
				}
			}).then(count => {
				if (count === 0) {
					frm.add_custom_button(__("Resignation Withdrawal"), function () {
						frappe.new_doc("Employee Resignation Withdrawal", {
							employee_resignation: frm.doc.name,
							employee: frm.doc.employee
						});
					}, __("Actions"));
				}
			});
		}
	},

	employee: function (frm) {
		// Trigger server-side fetch_from fields and supervisor auto-fill
		if (frm.doc.employee) {
			frm.refresh_fields();
		}
	}
});
