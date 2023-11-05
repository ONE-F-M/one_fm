// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Check', {
	refresh: function(frm){
		if (frm.doc.docstatus==0){
			frm.toggle_reqd(['attendance_status'], 1);
		}
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
});
