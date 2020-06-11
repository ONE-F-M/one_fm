// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('GP Letter Request', {
	refresh: function(frm) {

		frm.set_query("supplier_category", function(frm) {
            return {
                filters: {
                    "parent_item_group": 'All Item Groups'
                }
            }
        });


        frm.set_query("supplier_subcategory", function(frm) {
            return {
                filters: {
                    "parent_item_group": 'Null'
                }
            }
        });


        // frm.set_query("supplier", function(frm) {
        //     return {
        //         filters: {
        //             "name": 'Null'
        //         }
        //     }
        // });


	},
	supplier_category: function(frm) {
		frm.set_value("supplier_subcategory", );
		frm.set_value("supplier", );
		frm.set_value("supplier_name", );

		frm.set_query("supplier_subcategory", function(frm) {
            return {
                filters: {
                    "parent_item_group": cur_frm.doc.supplier_category
                }
            }
        });

	},
	supplier_subcategory: function(frm) {
		frm.set_value("supplier", );
		frm.set_value("supplier_name", );


        // cur_frm.set_query("supplier", function() {
        //     return {
        //         query: "one_fm.one_fm.doctype.gp_letter_request.gp_letter_request.get_suppliers",
        //         filters: {
        //             supplier_group: cur_frm.doc.supplier_category,
        //             supplier_subgroup: cur_frm.doc.supplier_subcategory
        //         }         
        //     };
        // });




	},
    supplier: function(frm) {
        frm.set_value("supplier_name", );
        frm.set_value("sent_date", );
        frm.set_value("reminder1", );
        frm.set_value("reminder2", );
        
        frm.set_value("upload_reminder1", );
        frm.set_value("upload_reminder2", );
        frm.set_value("upload_reminder3", );
        frm.set_value("upload_reminder4", );

        frm.set_value("gp_status", );
        frm.set_value("accept_date", );


        frm.call({
            method: "generate_new_pid",
            doc: frm.doc,
            callback: function(r) {
                if(r.message){
                    
                }
            }
        })


    }
});
