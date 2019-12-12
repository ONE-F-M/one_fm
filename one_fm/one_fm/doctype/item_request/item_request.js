// Copyright (c) 2019, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Request', {
	refresh: function(frm) {
		if(!cur_frm.doc.project){
			frm.set_query("site", function() {
		        return {
		            "filters": {
		                "name": ""
		            }
		        };
		    });
		}

			// frappe.ui.form.on("Item Request Item", "total_amount", function (frm, cdt, cdn) {
			//     var total_amount = 0;
			//     $.each(frm.doc.items || [], function (i, d) {
			//         total_amount += flt(d.total_amount);
			//     });
			//     frm.set_value("total_amount", Math.round(total_amount));
			// });
	},
	project: function(frm){
		frm.set_value("site",)
		if(cur_frm.doc.project){

			frm.set_query("site", function() {
			    return {
					query: "one_fm.one_fm.doctype.item_request.item_request.get_data",
					filters: {
						project_parent: frm.doc.project
					}
			    };
			});
		}
	},
	site: function(frm){
		if(!cur_frm.doc.project){
			frm.set_query("site", function() {
		        return {
		            "filters": {
		                "name": ""
		            }
		        };
		    });
		}
	}
});


// frappe.ui.form.on('Item Request Item', {
//     qty: function (frm, cdt, cdn) {
//     	var row = locals[cdt][cdn];
//         if (row.qty && row.unit_price) {
//             frappe.model.set_value(cdt, cdn, "total_amount", row.qty*row.unit_price);
//         }
//     },
//     unit_price: function (frm, cdt, cdn) {
//     	var row = locals[cdt][cdn];
//         if (row.qty && row.unit_price) {
//             frappe.model.set_value(cdt, cdn, "total_amount", row.qty*row.unit_price);
//         }
//     }
// });


// frappe.ui.form.on("Item Request Item", "total_amount", function (frm, cdt, cdn) {
//     var total_amount = 0;
//     $.each(frm.doc.items || [], function (i, d) {
//         total_amount += flt(d.total_amount);
//     });
//     frm.set_value("total_amount", Math.round(total_amount));
// });
