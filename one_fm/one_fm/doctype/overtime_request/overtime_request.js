// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Overtime Request', {
	
	// Updating the `naming_series` upon request type (eg: request type: Head Office - naming: OT-HO-HR-EMP-00004)
	request_type: function(frm) {
		if (frm.doc.request_type == "Operations"){
			frm.set_value("naming_series", "OT-OP-.{employee}.-");
		}else if (frm.doc.request_type == "Head Office"){
			frm.set_value("naming_series", "OT-HO-.{employee}.-");
		}
	},
	employee: function(frm) {
		if (frm.doc.request_type == "Operations"){
			frm.set_value("naming_series", "OT-OP-.{employee}.-");
		}else if (frm.doc.request_type == "Head Office"){
			frm.set_value("naming_series", "OT-HO-.{employee}.-");
		}
	},
});
