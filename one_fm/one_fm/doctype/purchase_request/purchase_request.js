// Copyright (c) 2019, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Request', {
	validate: function(frm) {

			frappe.ui.form.on("Purchase Request Item", "total_amount", function (frm, cdt, cdn) {
			    var total_amount = 0;
			    $.each(frm.doc.items || [], function (i, d) {
			        total_amount += flt(d.total_amount);
			    });
			    frm.set_value("total_amount", Math.round(total_amount));
			});
	},
	project: function(frm){
		if(cur_frm.doc.project){

			frm.set_query("site", function() {
			    return {
					query: "one_fm.one_fm.doctype.purchase_request.purchase_request.get_data",
					filters: {
						project_parent: frm.doc.project
					}
			    };
			});
			
		}

	}
});


frappe.ui.form.on('Purchase Request Item', {
    qty: function (frm, cdt, cdn) {
    	var row = locals[cdt][cdn];
        if (row.qty && row.unit_price) {
            frappe.model.set_value(cdt, cdn, "total_amount", row.qty*row.unit_price);
        }
    },
    unit_price: function (frm, cdt, cdn) {
    	var row = locals[cdt][cdn];
        if (row.qty && row.unit_price) {
            frappe.model.set_value(cdt, cdn, "total_amount", row.qty*row.unit_price);
        }
    }
});


frappe.ui.form.on("Purchase Request Item", "total_amount", function (frm, cdt, cdn) {
    var total_amount = 0;
    $.each(frm.doc.items || [], function (i, d) {
        total_amount += flt(d.total_amount);
    });
    frm.set_value("total_amount", Math.round(total_amount));
});


// frappe.ui.form.on("Purchase Request Item", "qty", function (frm, cdt, cdn) {
//     var total_amount = 0;
//     $.each(frm.doc.items || [], function (i, d) {
//         total_amount += flt(d.qty)*flt(d.unit_price);
//     });
//     frm.set_value("total_amount", Math.round(total_amount));
// });


// frappe.ui.form.on("Purchase Request Item", "unit_price", function (frm, cdt, cdn) {
//     var total_amount = 0;
//     $.each(frm.doc.items || [], function (i, d) {
//         total_amount += flt(d.qty)*flt(d.unit_price);
//     });
//     frm.set_value("total_amount", Math.round(total_amount));
// });
