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
	let {employee, emp_name, date, permission_type} = frm.doc;
	if(employee != undefined && date != undefined && permission_type != ''){
		frappe.db.get_value("Shift Assignment", {date, employee}, "*")
		.then(res => {
			if(Object.keys(res).length === 0 && res.constructor === Object){
				frappe.msgprint(__(`No shift assigned to ${emp_name} on ${moment(date).format("DD-MM-YYYY")}. Please check again.`));				
				set_shift_details(frm, undefined, undefined, undefined, undefined);
			}
			else{
				let {name, shift, shift_type} = res.message;
				frappe.db.get_value("Operations Shift", shift, ["supervisor", "supervisor_name"])
				.then(res => {
					let {supervisor, supervisor_name} = res.message;
					set_shift_details(frm, name, supervisor, shift, shift_type);			
				});
			}
		})
	}
}

function set_shift_details(frm, name, supervisor, shift, shift_type){
	frappe.model.set_value(frm.doctype, frm.docname, "assigned_shift", name);
	frappe.model.set_value(frm.doctype, frm.docname, "shift_supervisor", supervisor);
	frappe.model.set_value(frm.doctype, frm.docname, "shift", shift);
	frappe.model.set_value(frm.doctype, frm.docname, "shift_type", shift_type);
}