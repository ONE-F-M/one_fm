// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shift Assignment Checker", {
	refresh(frm) {
        if (frm.doc.attendance_manager == frappe.session.user && frm.doc.shift_assignment_created == 0){
            frm.add_custom_button(__("Create Shift Assignment"), () =>
				frappe.call({
					method:
						"one_fm.one_fm.doctype.shift_assignment_checker.shift_assignment_checker.create_shift_assignment",
					args: {doc: frm.doc},
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint("Shift Assignment Created")
						}
					},
				})
		    );
        }
	},
});
