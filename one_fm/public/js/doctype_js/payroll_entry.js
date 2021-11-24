frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
			frm.set_indicator_formatter('employee',
					function(doc) {
						return (doc.justification_needed_on_deduction == 1) ? "orange" : "green";
					}
			);
    }
});
