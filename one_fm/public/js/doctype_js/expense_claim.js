frappe.ui.form.on('Expense Claim', {
	refresh: function(frm) {
		// set field and toggle
		set_toggle_fields(frm);
	},
	expense_approver: frm=>{
		if(frm.doc.expense_approver==frappe.session.user){
			toggle_accounting_display(frm, 1);
		} else {
			toggle_accounting_display(frm, 0);
		}
	}
});

let set_toggle_fields  = frm => {
	// set account payable
	if(frm.is_new()){
		// toggle accounting section
		frm.toggle_reqd('payable_account', 0);
		frm.set_value('payable_account', 'Account Payable - ONEFM');
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
		if((frappe.session.user==frm.doc.expense_approver) || has_role){
			toggle_accounting_display(frm, 1);
		} else {
			toggle_accounting_display(frm, 0);
		}
	}
}

let toggle_accounting_display = (frm, state) => {
	// hide/unhide accounting and dimension
	if(state==1){
		frm.toggle_display('accounting_details', 1);
		frm.toggle_display('accounting_dimensions_section', 1);
	} else {
		frm.toggle_display('accounting_details', 0);
		frm.toggle_display('accounting_dimensions_section', 0);
	}
}
