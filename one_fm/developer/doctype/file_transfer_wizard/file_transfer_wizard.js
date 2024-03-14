// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on("File Transfer Wizard", {
	refresh(frm) {
        if(frm.doc.transfer_status =="Ready"){
            frm.add_custom_button(`Hey ${frappe.session.user} ! Click me to start`,()=>{
                frappe.call({
                    doc: frm.doc,
                    method: 'initiate_transfers',
                    callback: function(r) {
                        if(!r.exc){
                            frappe.show_alert(`Files are being copied over to  <b>${frm.doc.directory} </b> in  <b> ${frm.doc.url || frm.doc.ip_address} </b>`)
                        }
                    }
                });
            })
        }
	},
});
