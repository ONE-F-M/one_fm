// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Uniform', {
	employee: function(frm) {
		set_uniform_details(frm);
	},
	type: function(frm) {
		set_uniform_details(frm);
	}
});

frappe.ui.form.on('Employee Uniform Item', {
	uniforms_add: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(frm.doc.issued_on) {
			row.expire_on = frappe.datetime.add_months(frm.doc.issued_on, 12);
			refresh_field("expire_on", cdn, "uniforms");
		}
	}
});

var set_uniform_details = function(frm) {
	frm.clear_table('uniforms');
	if(frm.doc.employee && frm.doc.type && frm.doc.designation){
		frappe.call({
			doc: frm.doc,
			method: 'set_uniform_details',
			callback: function(r) {
				if(!r.exc){
					frm.refresh_fields()
				}
			},
			freeze: true,
			freeze_message: __('Fetching Uniform Details..')
		});
	}
};
