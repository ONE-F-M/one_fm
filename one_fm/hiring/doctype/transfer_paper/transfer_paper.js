
// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transfer Paper', {
    onload: function(frm){
        set_wp_status(frm);
    },
    refresh: function(frm) {
        let doc_name = frm.doc.name;
        // console.log(doc_name)
        if(frm.doc.docstatus==1) {
                frm.add_custom_button(__('Re-Send'), function() { 
                    frappe.xcall('one_fm.hiring.doctype.transfer_paper.transfer_paper.resend_new_wp_record',{doc_name})
                    frappe.msgprint({
                        title: __('Notification'),
                        indicator: 'green',
                        message: __('Old Work Permit Record is rejected / created new record Sucessfully')
                    });
                })
                frm.add_custom_button(__('Close'), function() {
                    frappe.xcall('one_fm.hiring.doctype.transfer_paper.transfer_paper.closed_old_wp_record',{doc_name})
                
                frappe.msgprint({
                    title: __('Notification'),
                    indicator: 'green',
                    message: __('Previous Work Permit Record is Closed Sucessfully')
                    });
                })
            
        }
    }
    
});
var set_wp_status = function(frm){
    frappe.call({
        method:"frappe.client.get_value",//api calls
        args: {
            doctype:"Work Permit",
            filters: {
            name: frm.doc.employee
            },
            fieldname:["work_permit_status"]
        }, 
        callback: function(r) { 
            frm.set_value('work_permit_status', r.message.work_permit_status);
        }
    })
}
