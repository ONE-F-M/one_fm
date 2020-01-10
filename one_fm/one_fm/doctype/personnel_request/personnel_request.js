// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Personnel Request', {
	validate: function(frm) {
		if(!frm.doc.agency && !frm.doc.company){
			frappe.throw("Agency or Company is Required")
		}
	}
});
