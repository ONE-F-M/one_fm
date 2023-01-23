frappe.ui.form.on('Employee Checkin', {
	refresh: function(frm) {
	    if (!frappe.user.has_role('System Manager')){
		    frm.disable_form();
	    }
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
