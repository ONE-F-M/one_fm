// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Port of the BA Client Script "Testing new details fetech".
frappe.ui.form.on("Employee Record Update Request Properties Item", {
	property(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		frappe.model.set_value(cdt, cdn, "new_value", "");

		if (!row.property) {
			frappe.model.set_value(cdt, cdn, "new_value_doctype", "");
			return;
		}

		frappe.db
			.get_value("Record Update Property", row.property, ["linked_doctype", "employee_field"])
			.then((r) => {
				const p = r.message || {};

				frappe.model
					.set_value(cdt, cdn, "new_value_doctype", p.linked_doctype || "")
					.then(() => frm.refresh_field("properties"));

				// Current Details
				if (frm.doc.employee && p.employee_field) {
					frappe.db.get_value("Employee", frm.doc.employee, p.employee_field).then((res) => {
						const val = (res.message || {})[p.employee_field] || "";
						frappe.model.set_value(cdt, cdn, "old_value", val);
					});
				}
			});
	},
});
