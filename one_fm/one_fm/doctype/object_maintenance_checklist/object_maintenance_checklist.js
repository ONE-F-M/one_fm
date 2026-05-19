// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Object Maintenance Checklist", {
	refresh(frm) {
		resequence_tasks(frm);
	},
});

frappe.ui.form.on("Object Maintenance Checklist Items", {
	object_maintenance_checklist_items_add(frm) {
		resequence_tasks(frm);
	},

	object_maintenance_checklist_items_remove(frm) {
		resequence_tasks(frm);
	},

	object_maintenance_checklist_items_move(frm) {
		resequence_tasks(frm);
	},
});

function resequence_tasks(frm) {
	var items = frm.doc.object_maintenance_checklist_items || [];
	items.forEach(function (row, index) {
		frappe.model.set_value(row.doctype, row.name, "sequence_no", index + 1);
	});
	frm.refresh_field("object_maintenance_checklist_items");
}
