frappe.ui.form.on('Employee Checkin', {
	refresh: function(frm) {
	    if (!frappe.user.has_role('System Manager')){
		    frm.disable_form();
	    }
	    make_geolocation_map_read_only(frm);
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

var make_geolocation_map_read_only = (frm) => {
	// The Geolocation control's "locate me" button re-centers the map and
	// drops a marker at the browser's current position regardless of the
	// field's read_only setting, letting anyone reposition the map. Strip
	// it (and any draw control) so the map is view-only.
	const control = frm.fields_dict.geolocation;
	if (!control || !control.map) return;

	if (control.locate_control) {
		control.map.removeControl(control.locate_control);
		control.locate_control = null;
	}
	if (control.draw_control) {
		control.map.removeControl(control.draw_control);
		control.draw_control = null;
	}
}
