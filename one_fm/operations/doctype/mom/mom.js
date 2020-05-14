// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MOM', {
	site: function(frm) {
		let site = frm.doc.site;
		let project = frm.doc.project;
		if(site !== undefined && project !== undefined){
			frm.clear_table("attendees");
			get_poc_list(frm, "Operations Site", site);
			get_poc_list(frm, "Operations Project", project);
		}
	}
});

function get_poc_list(frm, doctype, name){
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype,
			name
		},
		callback: function(r) {
			if(!r.exc) {
				set_table(frm, r.message.poc);
			}
		}
	});
}


function set_table(frm, poc_list){

	poc_list.forEach((poc) => {
		let child_row = frappe.model.add_child(frm.doc, "attendees");
		child_row.poc_name = poc.poc;
		child_row.poc_designation = poc.designation;
	});
	frm.refresh_fields("attendees");
}
