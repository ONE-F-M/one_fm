// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Request', {
	refresh: function(frm) {

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

        if (row.requested_quantity && drow.unit_price) {
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


        $.each(frm.doc.suppliers_quotation || [], function (i, d) {

        	if(row.idx!=d.idx){
	    		frappe.model.set_value(d.doctype, d.name, "approved", 0);
	    	}
	    });


    }

});



frappe.ui.form.on("Purchase Request Item", "total_amount", function (frm, cdt, cdn) {
    var total = 0;
    $.each(frm.doc.items || [], function (i, d) {
        total += flt(d.total_amount);
    });
    frm.set_value("amount", total);
});

