// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Request', {
	refresh: function(frm) {
        

        cur_frm.set_query("site", function() {
            return {
                query: "one_fm.one_fm.doctype.purchase_request.purchase_request.get_sites",
                filters: {
                    project: cur_frm.doc.code
                }         
            };
        });



	},
	validate: function(frm) {
		var total = 0;
	    $.each(frm.doc.items || [], function (i, d) {
	        total += flt(d.total_amount);
	    });
	    frm.set_value("amount", total);

	}
});


frappe.ui.form.on('Purchase Request Item', {
    requested_quantity: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        if (row.requested_quantity && row.unit_price) {
            frappe.model.set_value(cdt, cdn, "total_amount", row.requested_quantity * row.unit_price);
        }
    },
    unit_price: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        if (row.requested_quantity && row.unit_price) {
            frappe.model.set_value(cdt, cdn, "total_amount", row.requested_quantity * row.unit_price);
        }
    }

});



frappe.ui.form.on('Suppliers Quotation', {
    approved: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        if (row.approved==0) {
            frappe.model.set_value(cdt, cdn, "reason", );
        }

    }

});



frappe.ui.form.on("Purchase Request Item", "total_amount", function (frm, cdt, cdn) {
    var total = 0;
    $.each(frm.doc.items || [], function (i, d) {
        total += flt(d.total_amount);
    });
    frm.set_value("amount", total);
});


frappe.ui.form.on("Purchase Request Item", "selected", function (frm, cdt, cdn) {
    var items_status = [];
    $.each(frm.doc.items || [], function (i, d) {
        items_status.push(d.selected);
    });
    if(!items_status.includes(0)){
        frm.set_value("ordered", 1);
    }else{
        frm.set_value("ordered", 0);
    }
});



// cur_frm.set_query("supplier", "items", function (doc, cdt, cdn) {
//     var row = locals[cdt][cdn];
//     if (!row || row === undefined) {
//         return
//     }
//     var supplier_length = cur_frm.doc.suppliers_quotation.length
//     var supplier = []
//     for (var i = 0; i < supplier_length; i++) {
//         supplier.push(cur_frm.doc.suppliers_quotation[i].supplier)
//     }
//     return {
//         filters: [
//             ['Supplier', 'name', 'in', supplier]
//         ]
//     }
// });

