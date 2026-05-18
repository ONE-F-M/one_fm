// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Space", {
	refresh(frm) {
		frm.set_query("maintenance_floor", function () {
			if (frm.doc.building_name) {
				return {
					filters: {
						building_name: frm.doc.building_name,
					},
				};
			}
			return {};
		});
	},

	maintenance_floor(frm) {
		// When floor changes and building gets auto-filled, re-apply the filter
		if (frm.doc.building_name) {
			frm.set_query("maintenance_floor", function () {
				return {
					filters: {
						building_name: frm.doc.building_name,
					},
				};
			});
		}
	},
});
