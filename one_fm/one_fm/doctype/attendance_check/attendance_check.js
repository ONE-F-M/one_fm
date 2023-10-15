// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Check', {
	refresh: function(frm){
		if (frm.doc.docstatus==0){
			frm.toggle_reqd(['attendance_status'], 1);
		}
		validate_admin_approval(frm);
		
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
	// attendance_status: function(frm){
	// 	validate_admin_approval(frm);
	// }
	
});


var validate_admin_approval = frm =>{
	frappe.call({
		method: 'one_fm.one_fm.doctype.attendance_check.attendance_check.check_attendance_manager',
		args: {
			email: frappe.session.user
		},
		callback:(r) => {
			if (!r.message){
				var selectField = document.querySelector('select[data-fieldname="justification"]');
				var options = selectField.getElementsByTagName('option');

				for (var i = 0; i < options.length; i++) {
					if (options[i].value === "Approved by Administrator") {
						options[i].style.display = 'none';
						break;
					}
				}
			}
		},
	})
}