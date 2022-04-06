// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Asset', {
	onload: function(frm) {
		frm.set_query("item_code", function() {
			return {
				"filters": {
					"disabled": 0,
					//"is_fixed_asset": 1,
					"is_stock_item": 1
				}
			};
		});

		frm.set_query("department", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});

		frm.set_query("cost_center", function() {
			return {
				"filters": {
					"company": frm.doc.company,
				}
			};
		});
	},
	setup: function(frm) {
		frm.set_query("purchase_receipt", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_receipts",
				filters: { item_code: doc.item_code }
			}
		});
		frm.set_query("purchase_invoice", (doc) => {
			return {
				query: "erpnext.controllers.queries.get_purchase_invoices",
				filters: { item_code: doc.item_code }
			}
		});
	},
	refresh: function(frm) {
		frm.events.make_schedules_editable(frm);
		frm.trigger("toggle_reference_doc");
		if (frm.doc.docstatus == 0) {
			frm.toggle_reqd("finance_books", frm.doc.calculate_depreciation);
		}
	},
	make_schedules_editable: function(frm) {
		if (frm.doc.finance_books) {
			var is_editable = frm.doc.finance_books.filter(d => d.depreciation_method == "Manual").length > 0
				? true : false;

			frm.toggle_enable("schedules", is_editable);
			frm.fields_dict["schedules"].grid.toggle_enable("schedule_date", is_editable);
			frm.fields_dict["schedules"].grid.toggle_enable("depreciation_amount", is_editable);
		}
	},
	toggle_reference_doc: function(frm) {
		if (frm.doc.purchase_receipt && frm.doc.purchase_invoice && frm.doc.docstatus === 1) {
			frm.set_df_property('purchase_invoice', 'read_only', 1);
			frm.set_df_property('purchase_receipt', 'read_only', 1);
		}
		else if (frm.doc.is_existing_asset) {
			frm.toggle_reqd('purchase_receipt', 0);
			frm.toggle_reqd('purchase_invoice', 0);
		}
		else if (frm.doc.purchase_receipt) {
			// if purchase receipt link is set then set PI disabled
			frm.toggle_reqd('purchase_invoice', 0);
			frm.set_df_property('purchase_invoice', 'read_only', 1);
		}
		else if (frm.doc.purchase_invoice) {
			// if purchase invoice link is set then set PR disabled
			frm.toggle_reqd('purchase_receipt', 0);
			frm.set_df_property('purchase_receipt', 'read_only', 1);
		}
		else {
			frm.toggle_reqd('purchase_receipt', 1);
			frm.set_df_property('purchase_receipt', 'read_only', 0);
			frm.toggle_reqd('purchase_invoice', 1);
			frm.set_df_property('purchase_invoice', 'read_only', 0);
		}
	},
	item_code: function(frm) {
		// if(frm.doc.item_code) {
		// 	frm.trigger('set_finance_book');
		// }
	},
	asset_category: function(frm){
		if(frm.doc.item_code && frm.doc.asset_category) {
			frm.trigger('set_finance_book');
		}
	},
	set_finance_book: function(frm) {
		frappe.call({
			method: "one_fm.one_fm.doctype.customer_asset.customer_asset.get_item_details",
			args: {
				item_code: frm.doc.item_code,
				asset_category: frm.doc.asset_category
			},
			callback: function(r, rt) {
				if(r.message) {
					console.log(r.message)
					frm.set_value('finance_books', r.message);
				}
			}
		})
	},
	available_for_use_date: function(frm) {
		var depreciation_start_date = moment(frm.doc.available_for_use_date).endOf('month').format('YYYY-MM-DD')
        $.each(frm.doc.finance_books || [], function(i, d) {
            d.depreciation_start_date = depreciation_start_date;
		});
		refresh_field("finance_books");
	},
	is_existing_asset: function(frm) {
		frm.trigger("toggle_reference_doc");
		// frm.toggle_reqd("next_depreciation_date", (!frm.doc.is_existing_asset && frm.doc.calculate_depreciation));
	},
	purchase_receipt: (frm) => {
		frm.trigger('toggle_reference_doc');
		if (frm.doc.purchase_receipt) {
			if (frm.doc.item_code) {
				frappe.db.get_doc('Purchase Receipt', frm.doc.purchase_receipt).then(pr_doc => {
					frm.events.set_values_from_purchase_doc(frm, 'Purchase Receipt', pr_doc)
				});
			} else {
				frm.set_value('purchase_receipt', '');
				frappe.msgprint({
					title: __('Not Allowed'),
					message: __("Please select Item Code first")
				});
			}
		}
	},
	purchase_invoice: (frm) => {
		frm.trigger('toggle_reference_doc');
		if (frm.doc.purchase_invoice) {
			if (frm.doc.item_code) {
				frappe.db.get_doc('Purchase Invoice', frm.doc.purchase_invoice).then(pi_doc => {
					frm.events.set_values_from_purchase_doc(frm, 'Purchase Invoice', pi_doc)
				});
			} else {
				frm.set_value('purchase_invoice', '');
				frappe.msgprint({
					title: __('Not Allowed'),
					message: __("Please select Item Code first")
				});
			}
		}
	},
	
	set_values_from_purchase_doc: function(frm, doctype, purchase_doc) {
		frm.set_value('company', purchase_doc.company);
		frm.set_value('purchase_date', purchase_doc.posting_date);
		const item = purchase_doc.items.find(item => item.item_code === frm.doc.item_code);
		if (!item) {
			doctype_field = frappe.scrub(doctype)
			frm.set_value(doctype_field, '');
			frappe.msgprint({
				title: __(`Invalid ${doctype}`),
				message: __(`The selected ${doctype} doesn't contains selected Asset Item.`),
				indicator: 'red'
			});
		}
		frm.set_value('gross_purchase_amount', item.base_net_rate + item.item_tax_amount);
		frm.set_value('purchase_receipt_amount', item.base_net_rate + item.item_tax_amount);
		frm.set_value('location', item.asset_location);
	},
	// refresh: function(frm) {

	// }
});
