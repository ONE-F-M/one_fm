// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MOM', {
	site: function(frm) {
		let site = frm.doc.site;
		let project = frm.doc.project;
		if(site !== undefined && project !== undefined){
			frm.clear_table("attendees");
			get_poc_list(frm, "Project", project);
			get_poc_list(frm, "Operations Site", site);
		}
	},
	review_last_mom: function(frm) {
		if(frm.doc.review_last_mom == 1){
			frappe.call({
				method: 'one_fm.operations.doctype.mom.mom.review_last_mom',
				args: {
					"mom":frm.doc.name,
					"site":frm.doc.site
				},
				callback: function(r) {
					frm.set_value("last_mom_name", r.message.name);
					set_last_attendees_table(frm, r.message.attendees);
					set_last_action_table(frm, r.message.action);

				}
			})
		}
	},
	review_pending_actions: function(frm) {
		if(frm.doc.review_pending_actions == 1){
			frappe.call({
				method: 'one_fm.operations.doctype.mom.mom.review_pending_actions',
				args:{
					"project":frm.doc.project
				},
				callback: function(r) {
					set_pending_actions_table(frm,r.message);
				}
			})
		}
	},
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

function set_last_attendees_table(frm, poc_list){

	poc_list.forEach((mom_poc) => {
		let child_row = frappe.model.add_child(frm.doc, "last_attendees");
		child_row.poc_name = mom_poc.poc_name;
		child_row.poc_designation = mom_poc.poc_designation;
	});
	frm.refresh_fields("last_attendees");
}

function set_last_action_table(frm, action_list){

	action_list.forEach((mom_action) => {
		let child_row = frappe.model.add_child(frm.doc, "last_action");
		child_row.subject = mom_action.subject;
		child_row.priority = mom_action.priority;
		child_row.description = mom_action.description;
	});
	frm.refresh_fields("last_action");
}

function set_pending_actions_table(frm, action_list){

	action_list.forEach((mom_action) => {
		let child_row = frappe.model.add_child(frm.doc, "pending_actions");
		child_row.subject = mom_action.subject;
		child_row.priority = mom_action.priority;
		child_row.description = mom_action.description;
	});
	frm.refresh_fields("pending_actions");
}