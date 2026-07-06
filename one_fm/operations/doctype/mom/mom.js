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
		if(frm.doc.project && frm.doc.project_type != "External"){
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
						// Fetch live Task data for the last action table
						fetch_and_set_last_actions(frm);
					}
				})
			}
			else if (frm.doc.project_type == "Internal") {
				frappe.call({
					method: 'one_fm.operations.doctype.mom.mom.review_last_internal_mom',
					args: {
						"mom":frm.doc.name,
						"project":frm.doc.project
					},
					callback: function(r) {
						frm.set_value("last_mom_name", r.message.name);
						set_last_general_attendees_table(frm, r.message.general_attendance);
						// Fetch live Task data for the last action table
						fetch_and_set_last_actions(frm);
					}
				})
			}
			else{
				frm.clear_table("last_action")
			}
		}
		else {
			frm.clear_table("last_action");
			frm.refresh_fields("last_action");
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
			frm.clear_table("pending_actions");
			frm.refresh_fields("pending_actions");
			add_mark_done_button(frm);
		}
	},
	refresh: function(frm){
		if (!check_roles()){
			set_project_query_for_non_project_manager(frm);
		}
		lock_poc_attendance_table(frm);
		add_mark_done_button(frm);
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

function fetch_and_set_last_actions(frm) {
	if (!frm.doc.last_mom_name) {
		frm.clear_table("last_action");
		frm.refresh_fields("last_action");
		return;
	}
	frappe.call({
		method: "one_fm.operations.doctype.mom.mom.review_last_actions",
		args: {
			last_mom_name: frm.doc.last_mom_name,
			project: frm.doc.project
		},
		callback: function(r) {
			if (r.message) {
				set_last_action_table(frm, r.message);
			} else {
				frm.clear_table("last_action");
				frm.refresh_fields("last_action");
			}
		}
	});
}

function html_to_plain_text(html) {
	// Task descriptions are stored as rich HTML (ql-editor). The MOM Pending Action
	// "description" is a Small Text field, so raw markup shows through. Convert to
	// readable plain text: keep link URLs, turn block tags into line breaks.
	if (!html) {
		return "";
	}
	if (!/<[a-z][\s\S]*>/i.test(html)) {
		// Already plain text
		return html;
	}

	const container = document.createElement("div");
	container.innerHTML = html;

	// Replace anchors with their href so links remain visible
	container.querySelectorAll("a[href]").forEach((a) => {
		const href = a.getAttribute("href");
		const text = (a.textContent || "").trim();
		a.replaceWith(document.createTextNode(text && text !== href ? `${text} (${href})` : href));
	});

	// Turn block-level tags and <br> into newlines before extracting text
	container.querySelectorAll("br").forEach((br) => br.replaceWith(document.createTextNode("\n")));
	container.querySelectorAll("p, div, li, tr").forEach((el) => el.append(document.createTextNode("\n")));

	const text = container.textContent || "";
	return text
		.replace(/\n{3,}/g, "\n\n")   // collapse excess blank lines
		.replace(/[ \t]+\n/g, "\n")   // trim trailing spaces on lines
		.trim();
}

function set_last_action_table(frm, action_list){
	frm.clear_table("last_action");
	action_list.forEach((mom_action) => {
		let child_row = frappe.model.add_child(frm.doc, "last_action");
		child_row.task = mom_action.task;
		child_row.subject = mom_action.subject;
		child_row.status = mom_action.status;
		child_row.priority = mom_action.priority;
		child_row.description = html_to_plain_text(mom_action.description);
		child_row.user = mom_action.user;
		child_row.due_date = mom_action.due_date;
	});
	frm.refresh_fields("last_action");
}

function set_pending_actions_table(frm, action_list){
	frm.clear_table("pending_actions");
	action_list.forEach((mom_action) => {
		let child_row = frappe.model.add_child(frm.doc, "pending_actions");
		child_row.task = mom_action.task;
		child_row.subject = mom_action.subject;
		child_row.status = mom_action.status;
		child_row.priority = mom_action.priority;
		child_row.description = html_to_plain_text(mom_action.description);
		child_row.user = mom_action.user;
		child_row.due_date = mom_action.due_date;
	});
	frm.refresh_fields("pending_actions");
	add_mark_done_button(frm);
}

function add_mark_done_button(frm) {
	const grid = frm.fields_dict["pending_actions"] && frm.fields_dict["pending_actions"].grid;
	if (!grid) return;

	const has_items = frm.doc.pending_actions && frm.doc.pending_actions.length > 0;
	const is_checked = frm.doc.review_pending_actions == 1;

	if (!is_checked || !has_items) {
		if (grid.custom_buttons && grid.custom_buttons[__("Mark Done")]) {
			grid.custom_buttons[__("Mark Done")].addClass("hidden");
		}
		return;
	}

	// Add a custom button to the grid
	grid.add_custom_button(__("Mark Done"), function() {
		const selected = grid.get_selected_children();
		if (!selected || selected.length === 0) {
			frappe.msgprint(__("Please select at least one row to mark as done."));
			return;
		}

		const tasks_to_complete = selected
			.filter(row => row.task)
			.map(row => row.task);

		if (tasks_to_complete.length === 0) {
			frappe.msgprint(__("No linked tasks found in the selected rows."));
			return;
		}

		// Remove duplicates (same task could appear for multiple assignees)
		const unique_tasks = [...new Set(tasks_to_complete)];

		frappe.confirm(
			__("Mark {0} task(s) as Completed?", [unique_tasks.length]),
			function() {
				let completed = 0;
				frappe.dom.freeze(__("Marking tasks as Completed..."));

				Promise.all(
					unique_tasks.map((task_name) =>
						frappe.call({
							method: "one_fm.operations.doctype.mom.mom.mark_task_as_done",
							args: { task_name },
						})
					)
				)
					.then((results) => {
						completed = results.filter((res) => res && res.message && res.message.success).length;

						frappe.show_alert({
							message: __("{0} task(s) marked as Completed", [completed]),
							indicator: "green",
						});

						// Refresh the pending actions table
						frm.clear_table("pending_actions");
						frm.refresh_fields("pending_actions");
						frm.trigger("review_pending_actions");
					})
					.finally(() => {
						frappe.dom.unfreeze();
					});
				frappe.show_alert({
					message: __("{0} task(s) marked as Completed", [completed]),
					indicator: "green"
				});

				// Refresh the pending actions table
				frm.clear_table("pending_actions");
				frm.refresh_fields("pending_actions");
				frm.trigger("review_pending_actions");
			}
		);
	});
}

// Sync edits in last_action / pending_actions child tables back to the actual Task
frappe.ui.form.on("MOM Pending Action", {
	subject: function(frm, cdt, cdn) { sync_task_field(cdn, "subject"); },
	description: function(frm, cdt, cdn) { sync_task_field(cdn, "description"); },
	priority: function(frm, cdt, cdn) { sync_task_field(cdn, "priority"); },
	status: function(frm, cdt, cdn) { sync_task_field(cdn, "status"); },
	user: function(frm, cdt, cdn) { sync_task_field(cdn, "user"); },
	due_date: function(frm, cdt, cdn) { sync_task_field(cdn, "due_date"); },
});

function sync_task_field(cdn, fieldname) {
	const row = frappe.get_doc("MOM Pending Action", cdn);
	if (!row || !row.task) return;

	let args = { task_name: row.task };
	args[fieldname] = row[fieldname];

	frappe.call({
		method: "one_fm.operations.doctype.mom.mom.update_task_from_mom",
		args: args,
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.show_alert({
					message: __("Task {0} updated", [row.task]),
					indicator: "green"
				});
			}
		}
	});
}
