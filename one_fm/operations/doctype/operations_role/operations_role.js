// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Role', {
	refresh: function(frm) {
		frm.set_query("sale_item", function() {
			return {
				"filters": {
					"is_stock_item": 0,
				}
			};
		});
		let roles = ['HR Manager', 'HR User', 'Project User', 'Project Manager']
		let has_role = false;
		roles.every((item, i) => {
			if(frappe.user.has_role(item)){
				has_role = true;
				return false
			}
		});
		if(has_role){
			frm.set_df_property('status', 'read_only', false);
		} else {
			frm.set_df_property('status', 'read_only', true);
		}
	}
});
