// Copyright (c) 2019, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("PAM File", {
	pam_licenses_remove: function(frm) {
		set_license_counts(frm);
	}
});

frappe.ui.form.on("PAM Licenses", {
	status: function(frm) {
		set_license_counts(frm);
	},
	civil_id_number_for_licensing: function(frm) {
		set_license_counts(frm);
	}
});

// Live preview only; the server recalculates the same counts on save.
function set_license_counts(frm) {
	let active = 0;
	let inactive = 0;
	(frm.doc.pam_licenses || []).forEach(row => {
		if (!row.civil_id_number_for_licensing) return;
		if (row.status === "Inactive") {
			inactive++;
		} else {
			active++;
		}
	});
	frm.set_value("number_of_active_licenses", String(active));
	frm.set_value("number_of_inactive_licenses", String(inactive));
	frm.set_value("file_status", active ? "Active" : "Inactive");
}
