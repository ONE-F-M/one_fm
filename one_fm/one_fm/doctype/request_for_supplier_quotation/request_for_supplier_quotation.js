// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt


cur_frm.add_fetch('contact', 'email_id', 'email_id')
cur_frm.add_fetch('supplier', 'supplier_name', 'supplier_name')


frappe.ui.form.on('Request for Supplier Quotation', {
	setup: function(frm) {
		frm.fields_dict["suppliers"].grid.get_field("contact").get_query = function(doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				query: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_supplier_contacts",
				filters: {'supplier': d.supplier}
			}
		}
	},

	onload: function(frm) {
		frm.add_fetch('email_template', 'response', 'message_for_supplier');

		if(!frm.doc.message_for_supplier) {
			frm.set_value("message_for_supplier", __("Please supply the specified items at the best possible rates"))
		}
	},

	refresh: function(frm, cdt, cdn) {
		if (frm.doc.docstatus === 1) {

			frm.add_custom_button(__("Send Supplier Emails"), function() {
				frappe.call({
					method: "send_supplier_quotation_emails",
					doc: cur_frm.doc,
					freeze: true,
					callback: function(r){
						frm.reload_doc();
					}
				});
			});


		}

	},

	get_suppliers_button: function (frm) {
		var doc = frm.doc;
		var dialog = new frappe.ui.Dialog({
			title: __("Get Suppliers"),
			fields: [
				{
					"fieldtype": "Select",
					"label": __("Get Suppliers By"),
					"fieldname": "search_type",
					"options": ["Item Group"],
					"default": "Item Group",
					"reqd": 1
				},
				{
					"fieldtype": "Link",
					"label": __("Item Group"),
					"fieldname": "supplier_group",
					"options": "Item Group",
					"reqd": 0,
					"depends_on": "eval:doc.search_type == 'Item Group'",
					"filters": {'is_group': 1,'parent_item_group': ["!=", 'All Item Groups'],'name': ["!=", 'All Item Groups']},
				},
				// {
				// 	"fieldtype": "Button",
				// 	"label": __("Get Suppliers"),
				// 	"fieldname": "get_suppliers"
				// },
				// {
				// 	"fieldtype": "HTML",
				// 	"label": __("Selected Supplier For Quotation"),
				// 	"fieldname": "selected_supplier"
				// },
				// {
				// 	"fieldtype": "Section Break",
				// 	"fieldname": "section_break_0014"
				// },
				{
					"fieldtype": "Button",
					"label": __("Add All Suppliers"),
					"fieldname": "add_suppliers"
				},
				// {
				// 	"fieldtype": "Column Break",
				// 	"fieldname": "column_break_0014"
				// },
				// {
				// 	"fieldtype": "Button",
				// 	"label": __("Add Selected Suppliers"),
				// 	"fieldname": "add_selected_suppliers"

				// },

			]
		});

		dialog.fields_dict.add_suppliers.$input.click(function() {
			var args = dialog.get_values();
			if(!args) return;
			dialog.hide();

			//Remove blanks
			if(frm.doc.suppliers){
				for (var j = 0; j < frm.doc.suppliers.length; j++) {
					if(!frm.doc.suppliers[j].hasOwnProperty("supplier")) {
						frm.get_field("suppliers").grid.grid_rows[j].remove();
					}
				}
			}

			 function load_suppliers(r) {
				if(r.message) {
					for (var i = 0; i < r.message.length; i++) {
						var exists = false;
						if (r.message[i].constructor === Array){
							var supplier = r.message[i][0];
						} else {
							var supplier = r.message[i].name;
						}
						for (var j = 0; j < doc.suppliers.length;j++) {
							if (supplier === doc.suppliers[j].supplier) {
								exists = true;
							}
						}
						if(!exists) {
							var d = frm.add_child('suppliers');
							d.supplier = supplier;
							frm.script_manager.trigger("supplier", d.doctype, d.name);
						}
					}
				}
				else{
					frappe.msgprint(__("There are No Supplier having the Item Group {0}",[args.supplier_group]))
				}
				frm.refresh_field("suppliers");
			}

			if (args.supplier_group) {
				return frappe.call({
					method: "get_supplier_group_list",
					doc: cur_frm.doc,
					args: {
						'supplier_group': args.supplier_group,
					},
					callback: load_suppliers
				});
			}
		});

		// dialog.fields_dict.get_suppliers.$input.click(function() {
		// 	var args = dialog.get_values();
		// 	if(!args) return;

		// 	if (args.supplier_group) {
		// 		return frappe.call({
		// 			method: "get_supplier_group_list",
		// 			doc: cur_frm.doc,
		// 			args: {
		// 				'supplier_group': args.supplier_group,
		// 			},
		// 			callback: function(r) {
		// 				if(r.message){
		// 					var content_head = "<table style='width:100%;' class='table table-striped' id='selected_supliers'><thead><tr><th>Supplier</th><th>Selected</th></tr></thead><tbody>"
		// 					var content=''
		// 					var content_footer='</tbody></table>'

		// 					for (var i = 0; i < r.message.length; i++) {
		// 						if (r.message[i].constructor === Array){
		// 							var supplier = r.message[i][0];
		// 						} else {
		// 							var supplier = r.message[i].name;
		// 						}

		// 						content += "<tr><td>"+supplier+"</td><td><input type='checkbox' name='supplier_"+i+"' id='supplier_"+i+"'></td></tr>"
		// 					}

		// 					dialog.fields_dict.selected_supplier.$wrapper.html(content_head+content+content_footer)
		// 				}
		//             }
		// 		});
		// 	}

		// });


		// dialog.fields_dict.add_selected_suppliers.$input.click(function() {
		// 	var args = dialog.get_values();
		// 	if(!args) return;

		// 	if (args.supplier_group) {
		// 		return frappe.call({
		// 			method: "get_supplier_group_list",
		// 			doc: cur_frm.doc,
		// 			args: {
		// 				'supplier_group': args.supplier_group,
		// 			},
		// 			callback: function(r) {
		// 				if(r.message){
		// 					var content_head = "<table style='width:100%;' class='table table-striped' id='selected_supliers'><thead><tr><th>Supplier</th><th>Selected</th></tr></thead><tbody>"
		// 					var content=''
		// 					var content_footer='</tbody></table>'

		// 					for (var i = 0; i < r.message.length; i++) {
		// 						if (r.message[i].constructor === Array){
		// 							var supplier = r.message[i][0];
		// 						} else {
		// 							var supplier = r.message[i].name;
		// 						}

		// 						content += "<tr><td>"+supplier+"</td><td><input type='checkbox' name='supplier_"+i+"' id='supplier_"+i+"'></td></tr>"
		// 					}

		// 					dialog.fields_dict.selected_supplier.$wrapper.html(content_head+content+content_footer)
		// 				}
		//             }
		// 		});
		// 	}

		// });

		dialog.show();

	}
})

frappe.ui.form.on("Request for Supplier Quotation Supplier",{
	supplier: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn]
		frappe.call({
			method:"erpnext.accounts.party.get_party_details",
			args:{
				party: d.supplier,
				party_type: 'Supplier'
			},
			callback: function(r){
				if(r.message){
					frappe.model.set_value(cdt, cdn, 'contact', r.message.contact_person)
					frappe.model.set_value(cdt, cdn, 'email_id', r.message.contact_email)
				}
			}
		})
	}
})
