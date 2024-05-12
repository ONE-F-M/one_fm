// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Check', {
	refresh: function(frm){
		if (frm.doc.docstatus==0){
			frm.toggle_reqd(['attendance_status'], 1);
		}
		allow_only_attendance_manager(frm);
		screenshot_functionality(frm);
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
			frm.doc.justification = ""
			screenshot_functionality(frm);
		}
	},
	justification: function(frm){
		screenshot_functionality(frm);
		
	}
});



var screenshot_functionality = (frm) => {
	const show_screenshot = ["Invalid media content", "Mobile isn't supporting the app", "Employees insist that he/she did check in or out", "Other"].includes(frm.doc.justification)
	frm.toggle_reqd("screenshot", show_screenshot)
	frm.toggle_display("screenshot", show_screenshot)
}



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
