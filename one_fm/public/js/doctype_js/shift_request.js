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
            method: 'one_fm.api.doc_methods.shift_request',
            callback: function(r) {
                if(r.message){
                    console.log(r.message)
                }
            }
        });
    }
}