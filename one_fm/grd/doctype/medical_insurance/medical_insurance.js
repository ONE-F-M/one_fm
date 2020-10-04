// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Medical Insurance', {
	civil_id: function(frm) {
		if(frm.doc.civil_id){
			frappe.call({
				doc: frm.doc,
				method: 'get_employee_data_from_civil_id',
				callback: function(r) {
					frm.refresh_fields();
				},
				freaze: true,
				freaze_message: __("Fetching Data with CIVIL ID")
			});
		}
	}
});
