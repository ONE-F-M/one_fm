// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Designation Profile', {
	refresh: function(frm) {
		frm.set_query("item", "accommodation_assets", function() {
			return {
				filters: {
					"is_fixed_asset": true
				}
			}
		});
		frm.set_query("item", "accommodation_consumables", function() {
			return {
				filters: {
					"is_stock_item": true
				}
			}
		});
		frm.set_query("item", "uniforms", function() {
			return {
				filters: {
					"is_stock_item": true
				}
			}
		});
	}
});
