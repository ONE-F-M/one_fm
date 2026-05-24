// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Object", {
	object_template(frm) {
		if (!frm.doc.object_template) {
			return;
		}

		// Fetch parts from the template
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Object Template",
				name: frm.doc.object_template,
			},
			callback: function (r) {
				if (!r.message) return;

				var template = r.message;
				var template_items = template.object_template_items || [];

				if (template_items.length === 0) return;

				if (frm.doc.object_items && frm.doc.object_items.length > 0) {
					frappe.confirm(
						__("This will replace the existing Parts list with parts from the selected template. Continue?"),
						function () {
							populate_parts(frm, template_items);
						}
					);
				} else {
					populate_parts(frm, template_items);
				}
			},
		});
	},
});

function populate_parts(frm, template_items) {
	frm.clear_table("object_items");
	template_items.forEach(function (item) {
		var row = frm.add_child("object_items");
		row.item_name = item.item_name;
		row.description = item.description;
	});
	frm.refresh_field("object_items");
}
