// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Recruitment Trip Request', {
	// refresh: function(frm) {

	// }
	setup(frm) {
		frm.make_methods = {
			'Employee Advance': () => {
				open_form(frm, "Employee Advance", null, null);
			}		
		};
	}
	
});
function open_form(frm, doctype, child_doctype, parentfield) {
	frappe.model.with_doctype(doctype, () => {
        let new_doc = frappe.model.get_new_doc(doctype);
        new_doc.purpose   = 'Requesting an advance amount of ' + frm.doc.amount + ' for recruitment trip';
		new_doc.employee = frm.doc.employee;
		new_doc.recruitment_trip_request = frm.doc.name
		frappe.ui.form.make_quick_entry(doctype, null, null, new_doc);
	});
}