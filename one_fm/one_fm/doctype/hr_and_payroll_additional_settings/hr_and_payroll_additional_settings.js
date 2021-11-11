// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('HR and Payroll Additional Settings', {
	refresh: function(frm) {
		frm.set_query("holiday_compensatory_leave_type", function() {
			return {
				filters: {
					"is_compensatory": true
				}
			};
		});
		frm.set_query("holiday_additional_salary_component", function() {
			return {
				filters: {'type': 'Earning'}
			};
		});
	}
});
