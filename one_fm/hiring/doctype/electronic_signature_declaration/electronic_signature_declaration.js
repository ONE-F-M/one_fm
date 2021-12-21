// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Electronic Signature Declaration', {
	update: function(frm) {
		console.log("This")
		set_signature(frm);
	}
});

var set_signature = function(frm) {
	if(frm.applicant_signature){
		frappe.db.set_value('Onboard Employee', self.onboarding_employee, 'electronic_signature_declaration_status', 1)
	}
}