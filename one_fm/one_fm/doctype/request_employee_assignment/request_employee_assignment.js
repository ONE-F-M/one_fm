// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request Employee Assignment', {
	refresh: function(frm) {
		if(!frm.doc.__islocal){
			$('.actions-btn-group').hide();
			if (frm.doc.workflow_state == "Pending"){
				frm.add_custom_button('Approve', () =>{
					let {doctype, docname} = frm;
					frappe.xcall('one_fm.one_fm.doctype.request_employee_assignment.request_employee_assignment.approve_assignment_request',{doctype, docname})
					.then(res => {
						frm.reload_doc();
					});
				}).addClass("btn-primary");
				frm.add_custom_button('Reject', () => {
					let {doctype, docname} = frm;
					frappe.xcall('one_fm.one_fm.doctype.request_employee_assignment.request_employee_assignment.reject_assignment_request',{doctype, docname})
					.then(res => {
						frm.reload_doc();
					});
				}).addClass("btn-danger");
			}
		}
	}
});
