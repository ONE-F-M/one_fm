// Copyright (c) 2019, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Check', {
    refresh: function(frm){

    },
    setup: function(frm) {
        frm.set_indicator_formatter('item_code',
            function(doc) {
                return (doc.qty<=doc.actual_qty) ? "green" : "orange"
        })
    },
	item_request: function(frm) {
		if(cur_frm.doc.item_request){
            cur_frm.doc.item_coding = []
            frappe.model.with_doc("Item Request", frm.doc.item_request, function() {
                var tabletransfer= frappe.model.get_doc("Item Request", frm.doc.item_request)
                frm.doc.item_coding = []
                frm.refresh_field("item_coding");
                $.each(tabletransfer.items, function(index, row){
                    var d = frm.add_child("item_coding");
                    d.item_code_name = row.item_name;
                    d.item_description = row.item_description;
                    d.qty = row.qty;
                    d.uom = row.uom;
                    frm.refresh_field("item_coding");
                });
            })
        }
	}
    
});


frappe.ui.form.on('Item Coding', {    
    item_code: function (frm,cdt,cdn) {
        var row = locals[cdt][cdn];
        if(row.item_code && row.warehouse){
            frappe.call({
                "method": "set_actual_qty",
                doc: cur_frm.doc,
                args: {
                    'item_code': row.item_code,
                    'warehouse': row.warehouse
                },
                callback: function (r) {
                    if(r.message){
                        frappe.model.set_value(cdt, cdn, 'actual_qty', r.message);
                    }else{
                        frappe.model.set_value(cdt, cdn, 'actual_qty', 0.0);
                    }
                }
            });
        }else{
            frappe.model.set_value(cdt, cdn, 'actual_qty', 0.0);
        }
    },
    warehouse: function (frm,cdt,cdn) {
        var row = locals[cdt][cdn];
        if(row.item_code && row.warehouse){
            frappe.call({
                "method": "set_actual_qty",
                doc: cur_frm.doc,
                args: {
                    'item_code': row.item_code,
                    'warehouse': row.warehouse
                },
                callback: function (r) {
                    if(r.message){
                        frappe.model.set_value(cdt, cdn, 'actual_qty', r.message);
                    }else{
                        frappe.model.set_value(cdt, cdn, 'actual_qty', 0.0);
                    }
                }
            });
        }else{
            frappe.model.set_value(cdt, cdn, 'actual_qty', 0.0);
        }
    }

});

