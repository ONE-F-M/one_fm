// Copyright (c) 2019, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Check', {
    refresh: function(frm){

            cur_frm.set_query("parent_item_group", "item_coding", function(doc, cdt, cdn) {
                var d = locals[cdt][cdn];
                return{
                    filters: [
                        ['Item Group', 'parent_item_group', '=', 'All Item Groups']
                    ]
                }
            });

            cur_frm.set_query("subitem_group", "item_coding", function(doc, cdt, cdn) {
                var d = locals[cdt][cdn];
                return{
                    filters: [
                        ['Item Group', 'parent_item_group', '=', d.parent_item_group]
                    ]
                }
            });

            cur_frm.set_query("item_group", "item_coding", function(doc, cdt, cdn) {
                var d = locals[cdt][cdn];
                return{
                    filters: [
                        ['Item Group', 'parent_item_group', '=', d.subitem_group]
                    ]
                }
            });

            cur_frm.set_query("item_code", "item_coding", function(doc, cdt, cdn) {
                var d = locals[cdt][cdn];
                return{
                    filters: [
                        ['Item', 'item_group', '=', d.item_group]
                    ]
                }
            });

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
    },
    parent_item_group: function(frm,cdt,cdn) {
        var row = locals[cdt][cdn];
        if(row.parent_item_group){
            frappe.model.set_value(cdt, cdn, 'subitem_group', '');
            frappe.model.set_value(cdt, cdn, 'item_group', '');
            frappe.model.set_value(cdt, cdn, 'item_code', '');
        }
    },
    subitem_group: function(frm,cdt,cdn) {
        var row = locals[cdt][cdn];
        if(row.parent_item_group){
           frappe.model.set_value(cdt, cdn, 'item_group', '');
            frappe.model.set_value(cdt, cdn, 'item_code', '');
        }
    },
    item_group: function(frm,cdt,cdn) {
        var row = locals[cdt][cdn];
        if(row.parent_item_group){
            frappe.model.set_value(cdt, cdn, 'item_code', '');
        }
    }

});

