frappe.ui.form.on('Employee Checkin', {
	refresh: function(frm) {
	    if (!frappe.user.has_role('System Manager')){
		    frm.disable_form();
	    }
	    balance_shift_details_columns(frm);
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


var validate_source_of_checkin = (frm) => {
	var allowed_sources = ['Mobile App', 'Mobile Web']
	if(!allowed_sources.includes(frm.doc.source)){
		frappe.throw("Employee Checkin can only be via the Mobile App or Mobile Web App")
	}

}

var balance_shift_details_columns = (frm) => {
	// The "Shift Details" section splits fields into a fixed left/right Column
	// Break. Several fields in it hide via depends_on (shift_assignment-derived
	// fields) or auto-hide when read_only and empty, so one side can end up much
	// shorter than the other. CSS multi-column layout re-flows the same fields
	// across two visually balanced columns instead, recalculating live as fields
	// show/hide - no JS re-run needed after this.
	var section = $(frm.wrapper).find('.row[data-fieldname="shift_details"]').first();
	var body = section.find('> .section-body');
	if (!body.length) return;

	body.css({
		'display': 'block',
		'column-count': 2,
		'column-gap': '30px',
	});
	body.find('.form-column, .form-column > form').css('display', 'contents');
	body.find('.frappe-control').css({
		'break-inside': 'avoid',
		'width': '100%',
	});
}
