// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Residency Payment Request', {
	setup: function(frm) {
		frm.set_query("company_bank_account", function() {
			return {
				filters: {
					"is_company_account":1
				}
			}
		});
	},
	refresh: function(frm) {
		if (frm.doc.docstatus===1) {
			frm.add_custom_button(__('Create Payment'), function() {
				frm.trigger("make_payment_records");
			});
		}
	},
	make_payment_records: function(frm){
		// var dialog = new frappe.ui.Dialog({
		// 	title: __("For Supplier"),
		// 	fields: [
		// 		{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
		// 			"get_query": function () {
		// 				return {
		// 					query:"one_fm.grd.doctype.residency_payment_request.residency_payment_request.get_supplier_query",
		// 					filters: {'parent': frm.doc.name}
		// 				}
		// 			}, "reqd": 1
		// 		},
		//
		// 		{"fieldtype": "Link", "label": __("Mode of Payment"), "fieldname": "mode_of_payment", "options":"Mode of Payment",
		// 			"get_query": function () {
		// 				return {
		// 					query:"one_fm.grd.doctype.residency_payment_request.residency_payment_request.get_mop_query",
		// 					filters: {'parent': frm.doc.name}
		// 				}
		// 			}
		// 		}
		// 	]
		// });

		// var dialog = new frappe.ui.Dialog({
		// 	title: __("For Supplier"),
		// 	fields: [
		// 		{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier", "reqd": 1},
		// 		{"fieldtype": "Link", "label": __("Mode of Payment"), "fieldname": "mode_of_payment", "options":"Mode of Payment"}
		// 	]
		// });
		// dialog.set_primary_action(__("Submit"), function() {
		// 	var args = dialog.get_values();
		// 	if(!args) return;
		//
		// 	return frappe.call({
		// 		method: "one_fm.grd.doctype.residency_payment_request.residency_payment_request.make_payment_records",
		// 		args: {
		// 			"name": frm.doc.name,
		// 			"supplier": args.supplier,
		// 			"mode_of_payment": args.mode_of_payment
		// 		},
		// 		freeze: true,
		// 		callback: function(r) {
		// 			dialog.hide();
		// 			frm.refresh();
		// 		}
		// 	})
		// })
		//
		// dialog.show();

		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if(cur_frm.doc.__onload && cur_frm.doc.__onload.make_payment_via_journal_entry){
			method = "erpnext.accounts.doctype.journal_entry.journal_entry.get_payment_entry_against_invoice";
		}
		// return frappe.call({
		// 	method: method,
		// 	args: {
		// 		"dt": "Purchase Invoice",
		// 		"dn": "ACC-PINV-2020-00013"
		// 	},
		// 	callback: function(r) {
		// 		var doclist = frappe.model.sync(r.message);
		// 		frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		// 	},
		// 	freeze: true,
		// 	freeze_message: __('Creating Payment')
		// });
		return frappe.call({
			method: "one_fm.grd.doctype.residency_payment_request.residency_payment_request.make_payment",
			args: {
				"name": frm.doc.name,
				"method": "PE"
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
			freeze: true,
			freeze_message: __('Creating Payment')
		});
	},
	get_todays_residency_payment_details: function(frm) {
		frm.call({
			method: "set_todays_residency_payment_details",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.refresh_field("references");
			},
			freeze: true,
			freeze_message: __('Fetching Data...')
		});
	}
});

frappe.ui.form.on('Residency Payment Request Reference', {
	references_remove: function(frm) {
		calculate_total_amount(frm);
	}
});

var calculate_total_amount = function(frm) {
	let total_amount = 0;
	if(frm.doc.references){
		frm.doc.references.forEach((item, i) => {
			total_amount += item.amount?item.amount:0;
		});
	}
	frm.set_value('total_amount', total_amount);
};
