// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('MOM', {
	site: function(frm) {
		frm.clear_table("attendees");
		if(frm.doc.site){
			get_poc_list(frm, "Operations Site", frm.doc.site);
		}
		frm.refresh_fields("attendees");
	},
	project: function(frm) {
		if(!frm.doc.site){
			frm.clear_table("attendees");
		}
		if(frm.doc.project){
			get_project_type(frm, "Project", frm.doc.project);
			get_poc_list(frm, "Project", frm.doc.project);
		}
		frm.refresh_fields("attendees");

	},
	review_last_mom: function(frm) {
		if(frm.doc.review_last_mom == 1){
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: "Project",
					name: frm.doc.project
				},
				callback: function(r) {
					if(!r.exc) {
						if(r.message.project_type == "External"){
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
					}
				}
			});
		} else {
			frm.clear_table("last_action")
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
		} else {
			frm.clear_table("pending_actions")
		}
	},
	refresh: function(frm){
		if (!frappe.user_roles.includes("Projects Manager")){
			set_project_query_for_non_project_manager(frm);
		}
	},
	validate: function (frm){
		if (frm.is_new()){
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: "Project",
					name: frm.doc.project
				},
				callback: function(r) {
					if(!r.exc) {
						if(r.message.project_type != "External" && !frappe.user_roles.includes("Projects Manager")){
							frappe.throw("Only Project managers are allowed to create MOM for Non-External Projects")
		
						}
					}
				}
			});
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


var set_project_query_for_non_project_manager = (frm) => {
	frm.set_query("project", () => {
		return {
			filters: {
				project_type: "External"
			}
		}
	})
}


function get_project_type(frm, doctype, name){
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype,
			name
		},
		callback: function(r) {
			if(!r.exc) {
				if(r.message.project_type == "External"){
					frm.toggle_display("site", 1)

				} else {
					if (!frappe.user_roles.includes("Projects Manager")){
						frappe.throw("Only Project managers are allowed to create MOM for Non-External Projects")
					}
					set_table_non_external(frm, r.message.users)
					frm.toggle_display("issues", 0)
					frm.toggle_display("meeting_duration", 0)
					
				}
				
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


var set_table_non_external = (frm, user_list) => {
	if(user_list){
		const array_of_user = user_list.map(obj => obj.user);
		frappe.call({
			method: "one_fm.operations.doctype.mom.mom.fetch_designation_of_users",
			args: {
				"list_of_users": array_of_user
			},
			callback: function(r) {
				if (!r.exc && r.message){
					r.message.forEach((obj) => {
						let child_row = frappe.model.add_child(frm.doc, "attendees");
						child_row.poc_name = obj.employee_name;
						child_row.poc_designation = obj.designation;
					});
					frm.refresh_fields("attendees");

				}
			}

		}
		)
	}
	
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
		child_row.user = mom_action.user;
		child_row.due_date = mom_action.due_date;
	});
	frm.refresh_fields("pending_actions");
}
