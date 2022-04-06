// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning Objects', {
	setup: function(frm) {
		frm.set_query("object_type", function() {
			return {
				filters: {
					"object_category": frm.doc.object_category
				}
					
				
			}
		});

	}
	
	
	
	
	// refresh: function(frm) {

	// }
});
