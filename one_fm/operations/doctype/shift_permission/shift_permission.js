// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Permission', {
	onload: function(frm) {
		set_employee_from_the_session_user(frm);
	},
	refresh: function(frm) {
		set_options_for_permission_type(frm);
	},
	log_type: function(frm) {
		set_options_for_permission_type(frm);
	},
	employee: function(frm) {
		get_shift_assignment(frm);
	},
	date: function(frm) {
		validate_date(frm);
		get_shift_assignment(frm);
	},
	permission_type: function(frm) {
		get_shift_assignment(frm);
	},
	validate: function(frm){
		validate_date(frm)
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

function set_options_for_permission_type(frm) {
	if(frm.doc.log_type){
		if(frm.doc.log_type == 'IN'){
			frm.set_df_property('permission_type', 'options', ['', 'Arrive Late']);
		}
		else{
			frm.set_df_property('permission_type', 'options', ['', 'Leave Early']);
		}
	}
	else{
		frm.set_df_property('permission_type', 'options', ['Select Log Type first']);
	}
};

function get_shift_assignment(frm){
	let {employee, emp_name} = frm.doc;
	if(employee != undefined){
		frappe.call({
            method: 'one_fm.operations.doctype.shift_permission.shift_permission.fetch_approver',
            args:{
                'employee':employee
            },
            callback: function(r) {
				let val = r.message
                if(val && val.includes(null) != true){
					let [name, approver, shift, shift_type] = r.message;
					set_shift_details(frm, name, approver, shift, shift_type);
                }
				else{
					frappe.msgprint(__(`No shift assigned to ${emp_name}. Please check again.`));
					set_shift_details(frm, undefined, undefined, undefined, undefined);
				}
            }
        });
	}
}

function set_shift_details(frm, name, supervisor, shift, shift_type){
	frappe.model.set_value(frm.doctype, frm.docname, "assigned_shift", name);
	frappe.model.set_value(frm.doctype, frm.docname, "shift_supervisor", supervisor);
	frappe.model.set_value(frm.doctype, frm.docname, "shift", shift);
	frappe.model.set_value(frm.doctype, frm.docname, "shift_type", shift_type);
}


var validate_date = (frm) => {
	if (frm.doc.date){
		if (frm.doc.date < frappe.datetime.now_date()){
			if (frm.is_new()){
				frappe.throw("Please note that Shift permission cannot be created for a past date")

			} else {
				frappe.throw("Please note that Shift permission cannot be updated to a past date")
			}
		}
	}
}