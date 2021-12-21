// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Duty Commencement', {
	refresh: function(frm) {
		// Apply filters to get post types for a operations shift
		frm.set_query('post_type', function () {
			return {
				query: "one_fm.one_fm.page.roster.roster.get_filtered_post_types",
				filters: { 
					'shift': frm.doc.operations_shift 
				}
			};
		});
	}
});
