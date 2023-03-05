// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Checkin Issue', {
	refresh: function(frm) {
		if(!frm.doc.issue && frm.doc.workflow_state == 'Approved'){
			frm.add_custom_button(__('Create Issue'), function() {
				create_issue(frm);
			}).addClass('btn-primary');
		}
	},
	onload: function(frm) {
		set_employee_from_the_session_user(frm);
	},
	employee: function(frm) {
		get_shift_assignment(frm);
	}
});

function set_employee_from_the_session_user(frm) {
	if(frappe.session.user != 'Administrator' && frm.is_new()){
		frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'name', function(r) {
			if(r && r.name){
				frm.set_value('employee', r.name);
			}
			else{
				frappe.show_alert({
					message: __('Not find employee record for the user <b>{0}</b>', [frappe.session.user]),
					indicator: 'yellow'
				});
			}
		});
	}
};

function create_issue(frm) {
	frappe.call({
		method: 'create_issue',
		doc: frm.doc,
		freeze: true,
		freeze_message: __("Creating the Issue...!")
	})
};

function get_shift_assignment(frm){
	if(frm.doc.employee){
		frappe.call({
			method: 'one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue.fetch_approver',
			args:{
				'employee':frm.doc.employee
			},
			callback: function(r) {
				let val = r.message
				let assigned_shift, shift_supervisor, shift, shift_type = "";
				if(val && val.includes(null) != true){
					[assigned_shift, shift_supervisor, shift, shift_type] = r.message;
				}
				else{
					frappe.msgprint(__(`No shift assigned to ${frm.doc.employee_name}. Please check again.`));
				}
				frappe.model.set_value(frm.doctype, frm.docname, "assigned_shift", assigned_shift);
				frappe.model.set_value(frm.doctype, frm.docname, "shift_supervisor", shift_supervisor);
				frappe.model.set_value(frm.doctype, frm.docname, "shift", shift);
				frappe.model.set_value(frm.doctype, frm.docname, "shift_type", shift_type);
				frm.refresh_fields();
			}
		});
	}
};
