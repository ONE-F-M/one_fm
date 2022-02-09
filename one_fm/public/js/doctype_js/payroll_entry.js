frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
		if (frm.doc.salary_slips_created == 1){
			frm.add_custom_button(__("Download Payroll Bank Export"), function() {
				let payroll_entry = frm.doc.name
				window.open("/files/payroll-entry/" + payroll_entry + ".xlsx", "Download");
			}).addClass("btn-primary");
			frm.add_custom_button(__("Download Payroll Cash Export"), function() {
				let payroll_entry = "Cash-" + frm.doc.name
				window.open("/files/payroll-entry/" + payroll_entry + ".xlsx", "Download");
			}).addClass("btn-primary");
		}
		frm.set_indicator_formatter('employee',
				function(doc) {
					return (doc.justification_needed_on_deduction == 1) ? "orange" : "green";
				}
		);
    }
});
