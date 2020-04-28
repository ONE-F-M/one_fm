// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Purchase Order', {
    refresh: function(frm) {
        
    },
    purchase_request: function(frm) {

        cur_frm.doc.items = []
        frm.set_value("total_amount", 0);
        frappe.model.with_doc("Purchase Request", frm.doc.purchase_request, function() {
            var tabletransfer= frappe.model.get_doc("Purchase Request", frm.doc.purchase_request)
            frm.doc.items = []
            frm.refresh_field("items");
            $.each(tabletransfer.items, function(index, row){
                if(!row.selected){
                    var d = frm.add_child("items");
                    d.item_code = row.item_code;
                    d.item_name = row.item_name;
                    d.description = row.description;
                    d.qty = row.requested_quantity;
                    d.unit_price = row.unit_price;
                    d.total_amount = row.total_amount;
                    d.uom = row.uom;
                    d.purchase_request_item_id = row.name
                    frm.set_value("total_amount", cur_frm.doc.total_amount+row.total_amount);
                    frm.refresh_field("items");
                }
            });
            
        })



    },
    onload: function(frm) {
        frm.set_query("purchase_request", function() {
            return {
                filters: [
                    ['Purchase Request', 'docstatus', '=', 1],
                    ['Purchase Request', 'ordered', '=', 0]
                ]
            }
        });

	},
	validate: function(frm) {
		var total = 0;
	    $.each(frm.doc.items || [], function (i, d) {
	        total += flt(d.total_amount);
	    });
	    frm.set_value("total_amount", total);

	}
});



frappe.ui.form.on('Supplier Purchase Order Item', {
    qty: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        if (row.qty && drow.unit_price) {
            frappe.model.set_value(cdt, cdn, "total_amount", row.qty * row.unit_price);
        }
    },
    unit_price: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        if (row.qty && row.unit_price) {
            frappe.model.set_value(cdt, cdn, "total_amount", row.qty * row.unit_price);
        }
    }

});



frappe.ui.form.on("Supplier Purchase Order Item", "total_amount", function (frm, cdt, cdn) {
    var total = 0;
    $.each(frm.doc.items || [], function (i, d) {
        total += flt(d.total_amount);
    });
    frm.set_value("total_amount", total);
});



