// Copyright (c) 2023, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Check', {
	refresh: function(frm){
		if (frm.doc.docstatus==0){
			frm.toggle_reqd(['attendance_status'], 1);
		}
		allow_only_attendance_manager(frm);
		// Apply initial visibility and action state on form load
		toggle_verification_fields(frm);
	},
	before_workflow_action: function(frm){
		if(frm.doc.workflow_state == 'Pending Approval'){
			if (!frm.doc.justification) {
				frm.scroll_to_field('justification');
			}
			else if(!frm.doc.attendance_status) {
				frm.scroll_to_field('attendance_status');
			}
		}
	},
	attendance_status: function(frm){
		if (frm.doc.attendance_status != "Present"){
			frm.set_value("justification", "");
			frm.set_value("action", "");
			reset_verification_fields(frm);
		}
	},

	justification: function(frm) {
		// Reset all verification fields and action when justification changes
		reset_verification_fields(frm);
		toggle_verification_fields(frm);

		// Auto-set action for non-conditional justifications
		var justification = frm.doc.justification;

		if (justification === "Forgot to check in") {
			frm.set_value("action", "Penalize the Employee");
		} else if (justification === "Other" || justification === "Approved by Administrator") {
			frm.set_value("action", "No Action Required");
		} else if (!justification) {
			frm.set_value("action", "");
		}
	},

	// Story 5: Out-of-site location
	is_the_employee_physically_onsite: function(frm) {
		if (frm.doc.justification !== "Out-of-site location") return;

		if (frm.doc.is_the_employee_physically_onsite === "Yes") {
			frm.set_value("action", "Issue a New Mobile");
		} else if (frm.doc.is_the_employee_physically_onsite === "No") {
			frm.set_value("action", "Employee must check in at correct place");
		} else {
			frm.set_value("action", "");
		}
	},

	// Story 8: User not assigned to shift — first question
	is_the_employee_assigned_to_the_correct_shift: function(frm) {
		if (frm.doc.justification !== "User not assigned to shift") return;

		// Reset the secondary field
		frm.set_value("did_the_employee_try_to_check_in_outside_working_hours", "");

		if (frm.doc.is_the_employee_assigned_to_the_correct_shift === "No") {
			frm.set_value("action", "Penalize the Supervisor");
		} else if (frm.doc.is_the_employee_assigned_to_the_correct_shift === "Yes") {
			// Show secondary question, action will be set by it
			frm.set_value("action", "");
		} else {
			frm.set_value("action", "");
		}
	},

	// Story 8: User not assigned to shift — second question
	did_the_employee_try_to_check_in_outside_working_hours: function(frm) {
		if (frm.doc.justification !== "User not assigned to shift") return;
		if (frm.doc.is_the_employee_assigned_to_the_correct_shift !== "Yes") return;

		if (frm.doc.did_the_employee_try_to_check_in_outside_working_hours === "Yes") {
			frm.set_value("action", "Penalize the Employee");
		} else if (frm.doc.did_the_employee_try_to_check_in_outside_working_hours === "No") {
			frm.set_value("action", "Raise Ticket to Helpdesk");
		} else {
			frm.set_value("action", "");
		}
	},

	// Story 9: Mobile isn't supporting the app
	is_the_mobile_specification_up_to_the_standard: function(frm) {
		if (frm.doc.justification !== "Mobile isn't supporting the app") return;

		if (frm.doc.is_the_mobile_specification_up_to_the_standard === "No") {
			frm.set_value("action", "Issue a New Mobile");
		} else if (frm.doc.is_the_mobile_specification_up_to_the_standard === "Yes") {
			frm.set_value("action", "Raise Ticket to Helpdesk");
		} else {
			frm.set_value("action", "");
		}
	},

	// Story 10: Application is missing geolocation permissions
	were_proper_permissions_given_to_the_app: function(frm) {
		if (frm.doc.justification !== "Application is missing geolocation permissions") return;

		if (frm.doc.were_proper_permissions_given_to_the_app === "No") {
			frm.set_value("action", "Employee must correct app settings");
		} else if (frm.doc.were_proper_permissions_given_to_the_app === "Yes") {
			frm.set_value("action", "Issue a New Mobile");
		} else {
			frm.set_value("action", "");
		}
	},
});


/**
 * Reset all verification fields to empty
 */
var reset_verification_fields = function(frm) {
	frm.set_value("is_the_employee_physically_onsite", "");
	frm.set_value("is_the_employee_assigned_to_the_correct_shift", "");
	frm.set_value("did_the_employee_try_to_check_in_outside_working_hours", "");
	frm.set_value("is_the_mobile_specification_up_to_the_standard", "");
	frm.set_value("were_proper_permissions_given_to_the_app", "");
	frm.set_value("action", "");
};

/**
 * Toggle visibility of verification fields based on current justification (Story 8)
 * The depends_on in JSON handles most visibility, but this ensures dynamic behavior.
 */
var toggle_verification_fields = function(frm) {
	// Handled by depends_on in JSON — no extra toggling needed
	frm.refresh_fields();
};


var allow_only_attendance_manager = (frm) => {
	const time_difference_check = calculate_time_difference(frm.doc.creation, 48)
	if (time_difference_check && frm.doc.docstatus != 1){
		frappe.call(
			{
				"method": "one_fm.one_fm.doctype.attendance_check.attendance_check.check_attendance_manager",
				"args": {
					"email": frappe.session.user
				},
				callback: (r) => {
					if (!r.message){
						frm.page.clear_actions_menu();
						frm.set_df_property('attendance_status', 'read_only', 1)
						frm.set_df_property('justification', 'read_only', 1)
						frm.set_df_property('comment', 'read_only', 1)
					}

				}
			},
		)
	}
}


var calculate_time_difference = (date_time, hours_difference) => {
	var dateString = date_time;

	var dateObject = new Date(dateString);

	var timeDifference = new Date() - dateObject;

	var hoursDifference = timeDifference / (1000 * 60 * 60);

	return hoursDifference >= hours_difference;
}
