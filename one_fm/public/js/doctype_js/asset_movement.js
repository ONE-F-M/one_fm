frappe.ui.form.on('Asset Movement', {
    before_workflow_action:function(frm){
        if(frm.doc.delivery_receipt == undefined && frm.doc.workflow_state == 'Pending'){
            frappe.throw("Please attatch signed copy of delivery receipt.");
        }
    }
});