// Copyright (c) 2023, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontract Staff Request', {
	refresh: function(frm) {
		set_requester(frm);
		create_shortlist_button(frm);
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

var create_shortlist_button = (frm) => {
	if (frm.doc.workflow_state == "Approved" && frm.doc.docstatus == 1) {
		frm.add_custom_button(__("Create Subcontract Staff Shortlist"), function () {
			frappe.model.with_doctype("Subcontract Staff Shortlist", function () {
				const shortlist = frappe.model.get_new_doc("Subcontract Staff Shortlist");
				shortlist.subcontract_staff_request = frm.doc.name;
				shortlist.company = frm.doc.company;
				shortlist.date = frappe.datetime.get_today();
				// One shortlist row per requested person, carrying the gender and nationality asked for.
				(frm.doc.subcontracted_staff_request_detail || []).forEach((d) => {
					for (let i = 0; i < (d.number || 0); i++) {
						const row = frappe.model.add_child(shortlist, "subcontract_staff_shortlist_detail");
						row.gender = d.gender;
						row.nationality = d.nationality;
					}
				});
				frappe.set_route("Form", shortlist.doctype, shortlist.name);
			});
		}).addClass("btn-primary");
	}
};
