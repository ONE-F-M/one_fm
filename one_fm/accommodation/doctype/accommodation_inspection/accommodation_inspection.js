// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accommodation Inspection', {
	accommodation_inspection_template: function(frm) {
		if (frm.doc.accommodation_inspection_template) {
			return frm.call({
				method: "get_template_details",
				doc: frm.doc,
				callback: function() {
					refresh_field('readings');
				}
			});
		}
	}
});
