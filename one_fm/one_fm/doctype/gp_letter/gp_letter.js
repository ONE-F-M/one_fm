// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('GP Letter', {
	refresh: function(frm) {

		// frm.set_query("supplier_category", function(frm) {
  //           return {
  //               filters: {
  //                   "parent_item_group": 'All Item Groups'
  //               }
  //           }
  //       });


  //       frm.set_query("supplier_subcategory", function(frm) {
  //           return {
  //               filters: {
  //                   "parent_item_group": 'Null'
  //               }
  //           }
  //       });


        // frm.set_query("supplier", function(frm) {
        //     return {
        //         filters: {
        //             "name": 'Null'
        //         }
        //     }
        // });


	},
	supplier_category: function(frm) {
		// frm.set_value("supplier_subcategory", );
		// frm.set_value("supplier", );
  //       frm.set_value("supplier_name", );

		// frm.set_query("supplier_subcategory", function(frm) {
  //           return {
  //               filters: {
  //                   "parent_item_group": cur_frm.doc.supplier_category
  //               }
  //           }
  //       });

	},
	supplier_subcategory: function(frm) {
		// frm.set_value("supplier", );
  //       frm.set_value("supplier_name", );


        // cur_frm.set_query("supplier", function() {
        //     return {
        //         query: "one_fm.one_fm.doctype.gp_letter.gp_letter.get_suppliers",
        //         filters: {
        //             supplier_group: cur_frm.doc.supplier_category,
        //             supplier_subgroup: cur_frm.doc.supplier_subcategory
        //         }         
        //     };
        // });




	}
});
