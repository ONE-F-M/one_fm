frappe.ui.form.on('Purchase Invoice', {
    validate: function(frm){
        if(frm.doc.__islocal || frm.doc.docstatus==0){
            if(frm.doc.supplier){
                set_expense_head(frm);
            }
        }     
    }
});
var set_expense_head = function(frm){
    frappe.call({
        method: 'frappe.client.get_value',
        args:{
            'doctype':'Supplier',
            'filters':{
                'name': frm.doc.supplier
            },
            'fieldname':[
                'expense_account'
            ]
        },
        callback:function(s){
            if (!s.exc) {
                $.each(frm.doc.items || [], function(i, v) {
                        frappe.model.set_value(v.doctype, v.name,"expense_account",s.message.expense_account)
                })
                frm.refresh_field("items");
            }
        }
    });
};