// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Assignment', {
	refresh: function(frm) {
		filter_active_employee(frm);
	},
	employee_availability: function(frm){
		if (frm.doc.employee_availability === 'Day Off'){
			frm.set_value('operations_role','');
			frm.doset_value('post_abbrv', '');
		}
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
