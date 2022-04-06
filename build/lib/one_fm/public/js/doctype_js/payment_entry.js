frappe.ui.form.on('Payment Entry', {
    get_outstanding_invoices: function(frm) {
        var filters = {'allocate_payment_amount' : 0 }
        frm.events.get_outstanding_documents(frm, filters);
        console.log(filters)
    }
});
frappe.ui.form.on('Payment Entry Reference', {
    is_allocate: function(frm,cdt,cdn) {
        let d = locals[cdt][cdn]
        let total_allocated_amount = 0, remaining_amount = 0;
        if(d.is_allocate){
            $.each(frm.doc.references || [], function(i, v) {
                total_allocated_amount += v.allocated_amount ;
            })
            remaining_amount = frm.doc.paid_amount - total_allocated_amount;
            if(remaining_amount > d.outstanding_amount){
                frappe.model.set_value(d.doctype, d.name,"allocated_amount", d.outstanding_amount)
            }
            else{
                frappe.model.set_value(d.doctype, d.name,"allocated_amount", remaining_amount)
            }
        }
        else{
            frappe.model.set_value(d.doctype, d.name,"allocated_amount", 0)
        }
    }
});