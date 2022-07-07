// Copyright (c) 2021, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Request', {
	employee: function(frm) {
		set_approver(frm)
	}
});

function set_approver(frm){
    if(frm.doc.employee){
        frappe.call({
            method: 'one_fm.api.doc_methods.shift_request.fetch_approver',
            args:{
                'employee':frm.doc.employee
            },
            callback: function(r) {
                console.log(r.message)
                if(r.message){
                    frm.set_value("approver",r.message)
                }
            }
        });
    }
}