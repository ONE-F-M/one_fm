frappe.ui.form.on('Employee Checkin', {
	refresh: function(frm) {
	    if (!frappe.user.has_role('System Manager')){
		    frm.disable_form();
	    }
	},
	validate: (frm) => {
		validate_source_of_checkin(frm);

	},
	employee: frm=>{
		frm.set_query('shift_assignment', () => {
			return {
				filters: {
					employee: frm.doc.employee
				}
			}
		})
	}
});


validate_source_of_checkin = (frm) => {
	allowed_sources = ['Mobile App', 'Mobile Web']
	if(!allowed_sources.includes(frm.doc.source)){
		frappe.throw("Employee Checkin can only be via the Mobile App or Mobile Web App")
	}
}
