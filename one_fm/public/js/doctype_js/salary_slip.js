frappe.ui.form.on('Salary Slip', {
	refresh: function(frm) {
		if (frm.doc.justification_needed_on_deduction == 1){
			frm.set_intro(__("Justification Needed on Deduction is True, Prepare Justification for PAM"), 'yellow');
		}
		// SET FIELDS DISPLAY FOR ROLES
		setFieldDisplay(frm);
	},
	employee:function(frm){
		if(frm.doc.employee){
			frappe.call({
				method: 'one_fm.overrides.salary_slip.validate_multi_structure_slip',
				args: {'doc':frm.doc},
				callback: function(r) {
					
					frappe.model.sync(r.message)
					frm.refresh_fields();

					
				}
			});
		}
	}
});


let setFieldDisplay = frm => {
	// hide earnings and gross for employee
	if (!(frappe.user_roles.includes('HR User')||frappe.user_roles.includes('HR Manager'))){
		['earnings', 'gross_pay', 'gross_year_to_date',
			'year_to_date', 'month_to_date'].forEach((item, i) => {
				frm.toggle_display(item, 0);
			});

	}
}
