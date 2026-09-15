// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance Schedule Entry", {
	object(frm) {
		// Object Category, Space and the location chain are auto-fetched
		// server-side on save from the master Object record.
	},

	maintenance_frequency(frm) {
		// Frequency (Days) is fetched from the linked Maintenance Frequency
		// (fetch_from), and the Planned Execution Datetime is derived on save.
	},
});
