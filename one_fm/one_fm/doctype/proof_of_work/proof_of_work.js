// Copyright (c) 2026, ONEFM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Proof of Work", {
	refresh(frm) {
		// WI-001703: download the POW Letter + Attendance Report as one ZIP.
		if (!frm.is_new()) {
			frm.add_custom_button(__("Export Zip File"), () => {
				const method = "one_fm.one_fm.doctype.proof_of_work.proof_of_work.export_zip";
				window.open(
					`/api/method/${method}?name=${encodeURIComponent(frm.doc.name)}`,
					"_blank"
				);
			});
		}
	},
});
