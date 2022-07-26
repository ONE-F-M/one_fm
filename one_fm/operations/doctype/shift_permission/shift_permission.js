// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Permission', {
	employee: function(frm) {
		get_shift_assignment(frm);
	},
	date: function(frm) {
		get_shift_assignment(frm);
	},
	permission_type: function(frm) {
		get_shift_assignment(frm);
	},
});

function get_shift_assignment(frm){
	let {employee, emp_name, start_date} = frm.doc;
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