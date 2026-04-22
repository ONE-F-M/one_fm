// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Pathfinder Log"),
				function () {
					frappe.new_doc("Pathfinder Log", {
						process_name: frm.doc.name,
					});
				},
				__("Create")
			);
		}
	},
});
