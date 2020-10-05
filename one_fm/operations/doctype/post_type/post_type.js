// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Post Type', {
	refresh: function(frm) {
		frm.set_query("sale_item", function() {
			return {
				"filters": {
					"is_stock_item": 0,
				}
			};
		});
	}
});