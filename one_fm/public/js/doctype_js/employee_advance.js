frappe.ui.form.on('Employee Advance', {
	refresh: function(frm) {
		// set field and toggle
		set_toggle_fields(frm);
	}
});

let set_toggle_fields  = frm => {
	// set account payable
	if(frm.is_new()){
		// toggle accounting section
		frm.toggle_reqd('advance_account', 0);
		frm.set_value('advance_account', 'Employee Advances - ONEFM');
		toggle_accounting_display(frm, 0);
	} else {
		let roles = ['HR Manager', 'Expense Approver', 'HR User',
			'Accounts User', 'Accounts Manager']
		let has_role = false;
		roles.every((item, i) => {
			if(frappe.user.has_role(item)){
				has_role = true;
				return false
			}
		});
		// if session user == approver
		if(has_role){
			toggle_accounting_display(frm, 1);
		} else {
			toggle_accounting_display(frm, 0);
		}
	}
}

let toggle_accounting_display = (frm, state) => {
	// hide/unhide accounting and dimension
	if(state==1){
		frm.toggle_display('advance_account', 1);
		frm.toggle_display('mode_of_payment', 1);
	} else {
		frm.toggle_display('advance_account', 0);
		frm.toggle_display('mode_of_payment', 0);
	}
}
