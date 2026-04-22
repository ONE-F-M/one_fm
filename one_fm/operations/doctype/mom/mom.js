// Copyright (c) 2020, ONE FM and contributors
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
		if(frm.doc.project_type != "External"){
			frappe.call({
                method: "one_fm.operations.doctype.mom.mom.get_project_users",
                args: {
                    project: frm.doc.project
                },
                callback(r) {
                    if (r.message) {
                        frm.clear_table("general_attendance");
                        r.message.forEach(user => {
                            let row = frm.add_child("general_attendance");
                            row.attendee_name = user;
                        });
                        frm.refresh_field("general_attendance");
                    }
                }
            });
        }
		if(!frm.doc.site){
			frm.clear_table("attendees");
		}
		if(frm.doc.project){
			set_site_filter(frm)
			get_project_type(frm, "Project", frm.doc.project);
			get_poc_list(frm, "Project", frm.doc.project);
		}
		frm.refresh_fields("attendees");

	},
	review_last_mom: function(frm) {
		if(frm.doc.review_last_mom == 1){
			if (frm.doc.project_type == "External"){
				frappe.call({
					method: 'one_fm.operations.doctype.mom.mom.review_last_external_mom',
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
			if (frm.doc.project_type == "Internal") {
				frappe.call({
					method: 'one_fm.operations.doctype.mom.mom.review_last_internal_mom',
					args: {
						"mom":frm.doc.name,
						"project":frm.doc.project
					},
					callback: function(r) {
						frm.set_value("last_mom_name", r.message.name);
						set_last_general_attendees_table(frm, r.message.general_attendance);
						set_last_action_table(frm, r.message.action);

					}
				})
				
			}
			else{
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
		if (!check_roles()){
			set_project_query_for_non_project_manager(frm);
		}
		lock_poc_attendance_table(frm);
	},
	validate: function (frm){
		if (frm.is_new()){
			if (frm.doc.project_type != "External" && !check_roles()){
				frappe.throw("You are not allowed to create MOM for Non-External Projects")
			}
		}
		validate_poc_general_attendance_attended(frm);
	}
	

});


var validate_poc_general_attendance_attended = (frm) => {
	const isAttended = frm.doc.attendees.some(obj => obj.attended_meeting) || frm.doc.general_attendance.some(obj => obj.attended_meeting);
	
	if (!isAttended) {
		frappe.throw(__("At least one POC or General Attendance must be marked present."));
	}

}



var check_roles = () => {
	const rolesToCheck = ["Projects Manager", "Site Supervisor"];
	const hasRole = rolesToCheck.some(role => frappe.user_roles.includes(role));
	return hasRole
}

/**
 * Locks the "POC Attendance" (attendees) child table so that:
 *   - The "Add Row" / "Add Multiple Rows" buttons are hidden.
 *   - Existing rows cannot be deleted (no delete button per row).
 *   - Header "select-all" checkbox and bulk Delete button are hidden.
 * The "General Attendance" table is intentionally left untouched.
 */
var lock_poc_attendance_table = (frm) => {
	const grid = frm.fields_dict["attendees"] && frm.fields_dict["attendees"].grid;
	if (!grid) return;

	// Prevent adding new rows programmatically
	grid.cannot_add_rows = true;

	// Prevent deleting existing rows programmatically
	grid.cannot_delete_rows = true;

	// Refresh so Frappe redraws the grid with the flags applied, then hide UI remnants
	grid.refresh();

	const $wrapper = grid.wrapper;

	// Hide "Add Row" / "Add Multiple Rows" buttons
	$wrapper.find(".grid-add-row, .grid-add-multiple-rows").addClass("hidden");

	// Hide header-level "select all" checkbox (first col in heading row)
	$wrapper.find(".grid-heading-row .col-xs-1").addClass("hidden");

	// Hide the bulk Delete button shown at the grid footer
	$wrapper.find(".grid-footer .btn-bulk-delete, .grid-footer .btn.btn-danger").addClass("hidden");

	// Hide per-row checkboxes and move handles (belt-and-suspenders)
	$wrapper.find(".col-move, .row-check").addClass("hidden");
}


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
				if(r.message.project_type != "External"){
					if (!check_roles()){
						frappe.throw("You are not allowed to create MOM for Non-External Projects")
					}
					if(r.message.users){
						set_table_non_external(frm, r.message.users)
					}
				}
			}
		}
	});
}

function set_site_filter(frm){
	frm.set_query('site', function () {
		return {
			filters: {
				'project': frm.doc.project,
			}
		};
	});
}

function is_attendee_already_added(attendee_list, poc){
	return Boolean(attendee_list.find(i => i.poc_name === poc))
}

function set_table(frm, poc_list){
	poc_list.forEach((poc) => {
		if(!is_attendee_already_added(frm.doc.attendees, poc.poc)) {
			let child_row = frappe.model.add_child(frm.doc, "attendees");
			child_row.poc_name = poc.poc;
			child_row.poc_designation = poc.designation;
		}
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
						if(!is_attendee_already_added(frm.doc.attendees, obj.employee_name)) {
							let child_row = frappe.model.add_child(frm.doc, "attendees");
							child_row.poc_name = obj.employee_name;
							child_row.poc_designation = obj.designation;
						}
					});
					frm.refresh_fields("attendees");

				}
			}

		}
		)
	}

}

function set_last_attendees_table(frm, poc_list){
	frm.doc.last_attendees = []
	poc_list.forEach((mom_poc) => {
		if(!is_attendee_already_added(frm.doc.last_attendees, mom_poc.poc_name)) {
			let child_row = frappe.model.add_child(frm.doc, "last_attendees");
			child_row.poc_name = mom_poc.poc_name;
			child_row.poc_designation = mom_poc.poc_designation;
			child_row.attended_meeting = mom_poc.attended_meeting;
		}
	});
	frm.refresh_fields("last_attendees");
}

function set_last_general_attendees_table(frm, poc_list){
	frm.doc.last_general_attendees = []
	poc_list.forEach((mom_poc) => {
			let child_row = frappe.model.add_child(frm.doc, "last_general_attendees");
			child_row.attended_meeting = mom_poc.attended_meeting;
			child_row.attendee_name = mom_poc.attendee_name;

		
	});
	frm.refresh_fields("last_general_attendees");
}

function set_last_action_table(frm, action_list){
	frm.doc.last_action = []
	action_list.forEach((mom_action) => {
		let child_row = frappe.model.add_child(frm.doc, "last_action");
		child_row.user = mom_action.user;
		child_row.due_date = mom_action.due_date;
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
