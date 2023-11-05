// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Assignment', {
	refresh: function(frm) {
		filter_active_employee(frm);
	}
});

function filter_active_employee(frm){
	frm.set_query('employee', () => {
		return {
				filters: {
						status: 'Active'
				}
		}
	})
}
