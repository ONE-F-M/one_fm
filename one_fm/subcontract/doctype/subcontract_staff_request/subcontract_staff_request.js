// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontract Staff Request', {
	refresh: function(frm) {
		set_requester(frm);
		add_create_shortlist_button(frm);
	}
});




var set_requester = (frm) => {
	if (frm.is_new()){
		frappe.db.get_value("Employee", {"user_id": frappe.session.user}, 'name')
			.then(r => {
				if (r.message){
					frm.set_value("requester", r.message.name)
				}
			})
	}
}


var add_create_shortlist_button = (frm) => {
	if (frm.doc.status == "Approved" && frm.doc.docstatus == 1){
			frm.add_custom_button(__("Create Subcontract Staff Shortlist"), function() {
				// frappe.set_route('Form', frm.doc.reference_type, frm.doc.reference_name);
		}).addClass("btn-primary");
	}
}