// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// The multi-accommodation attendance-check UI (MA2-11) lives on its own page,
// "Transportation Attendance Check" (/app/transportation-attendance-check),
// not on this form. See one_fm/.../page/transportation_attendance_check/.
frappe.ui.form.on("Transportation Manifest", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Attendance Check"), () => {
			frappe.set_route("transportation-attendance-check", frm.doc.name);
		});
	},
});
