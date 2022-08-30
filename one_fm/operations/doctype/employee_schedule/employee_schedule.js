// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Schedule', {
	refresh: frm => {
		filter_active_employee(frm);
	},
	shift : function(frm) {
		let {shift} = frm.doc;
		if(shift){
			frm.set_query("operations_role", function() {
				return {
					query: "one_fm.operations.doctype.employee_schedule.employee_schedule.get_operations_roles",
					filters: {shift}
				};
			});

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
