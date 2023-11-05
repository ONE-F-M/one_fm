frappe.ui.form.on('Employee Advance', {
	refresh: function(frm) {
		// set field and toggle
		set_toggle_fields(frm);
		if(cur_frm.doc.docstatus==1 && cur_frm.doc.status=="Paid"){
			cur_frm.add_custom_button(__('Purchase Invoice'), function() {
				let inv_doc = frappe.model.make_new_doc_and_get_name("Purchase Invoice");
				locals["Purchase Invoice"][inv_doc].employee_advance = frm.doc.name;
				frappe.set_route('Form', 'Purchase Invoice', inv_doc,{'company':frm.doc.company,'employee_advance':frm.doc.name});
			}, __('Create'));
		}

	}
});

let set_toggle_fields  = frm => {
	// set account payable
	if(frm.is_new()){
		// toggle accounting section
		frm.toggle_reqd('advance_account', 0);
		
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
	;
	if(state==1){
		
		frm.toggle_display('mode_of_payment', 1);
	} else {
		
		frm.toggle_display('mode_of_payment', 0);
	}
}
