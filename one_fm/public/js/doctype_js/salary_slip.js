frappe.ui.form.on('Salary Slip', {
	refresh: function(frm) {
		if (frm.doc.justification_needed_on_deduction == 1){
			frm.set_intro(__("Justification Needed on Deduction is True, Prepare Justification for PAM"), 'yellow');
		}
	}
});
