frappe.ui.form.on('Employee Incentive', {
	refresh: function(frm) {
		frm.set_query('leave_policy', function() {
			return {
				filters: {
					"docstatus": 1
				}
			};
		});
	},
});
