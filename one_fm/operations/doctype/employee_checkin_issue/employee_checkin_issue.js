// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Checkin Issue', {
	refresh: function(frm) {
		if(!frm.doc.ticket && frm.doc.workflow_state == 'Approved'){
			frm.add_custom_button(__('Create Ticket'), function() {
				create_ticket(frm);
			}).addClass('btn-primary');
		}
	},
	onload: function(frm) {
		set_employee_from_the_session_user(frm);
	},
	employee: function(frm) {
		get_shift_assignment(frm);
	},
	validate: function(frm){
		validate_date(frm);
	},
	date: function(frm){
		validate_date(frm);
	}

});


function validate_date(frm){
	if(frm.doc.date < frappe.datetime.now_date()){
		frappe.throw("Date can not be set to a past date")
	}

}

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

function create_ticket(frm) {
	frappe.call({
		method: 'create_hd_ticket',
		doc: frm.doc,
		freeze: true,
		freeze_message: __("Creating the Ticket!")
	})
};

function get_shift_assignment(frm){
	if(frm.doc.employee){
		frappe.call({
			method: 'one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue.fetch_approver',
			args:{
				'employee': frm.doc.employee,
				'date': frm.doc.date
			},
			callback: function(r) {
				let val = r.message
				let assigned_shift, approver, shift, shift_type = "";
				if(val){
					assigned_shift = val['assigned_shift']
					approver = val['shift_supervisor']
					shift = val['shift']
					shift_type = val['shift_type']
				}
				set_shift_details(frm, assigned_shift, approver, shift, shift_type);
			}
		});
	}
}

function set_shift_details(frm, assigned_shift, approver, shift, shift_type){
	frappe.model.set_value(frm.doctype, frm.docname, "assigned_shift", assigned_shift);
	frappe.model.set_value(frm.doctype, frm.docname, "shift_supervisor", approver);
	frappe.model.set_value(frm.doctype, frm.docname, "shift", shift);
	frappe.model.set_value(frm.doctype, frm.docname, "shift_type", shift_type);
}
