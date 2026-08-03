// Copyright (c) 2026, ONEFM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Proof of Work", {
	refresh(frm) {
		// WI-001808: the POW Letter and the Attendance Report are one PDF per contract -
		// Letter (summary + signature) first, Attendance Report (detail grid) after it.
		if (!frm.is_new()) {
			frm.add_custom_button(__("Download PDF"), () => {
				const method = "one_fm.one_fm.doctype.proof_of_work.proof_of_work.export_pdf";
				window.open(
					`/api/method/${method}?name=${encodeURIComponent(frm.doc.name)}`,
					"_blank"
				);
			});
		}
	},
});
