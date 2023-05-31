// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request for Purchase', {
	refresh: function(frm) {
		set_intro_related_to_status(frm);
		frm.events.make_custom_buttons(frm);
	},
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1 && frappe.user.has_role('Purchase Officer')){
			if(frm.doc.items.length > frm.doc.items_to_order.length && !frm.doc.notified_the_rfm_requester){
				frm.add_custom_button(__("Notify the Requester"),
					() => frm.events.notify_the_rfm_requester(frm));
			}

			frm.add_custom_button(__("Create Request for Quotation"),
				() => frm.events.make_request_for_quotation(frm), __('Actions'));

			if(frm.doc.__onload.exists_qfs){
				frm.add_custom_button(__("Compare Quotations"),
					() => frm.events.make_quotation_comparison_sheet(frm), __('Actions'));
			}

			frm.add_custom_button(__("Create Purchase Order"),
				() => frm.events.make_purchase_order(frm), __('Actions'));

			frm.page.set_inner_btn_group_as_primary(__('Actions'));
		}
	},
	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_purchase.request_for_purchase.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},
	notify_the_rfm_requester: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "notify_the_rfm_requester",
			callback: function(r) {
				console.log(r);
			},
			freeze: true,
			freeze_message: __("Notify The RFM Requester")
		});
	},
	make_quotation_comparison_sheet: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_purchase.request_for_purchase.make_quotation_comparison_sheet",
			frm: frm,
			run_link_triggers: true
		});
	},
	make_purchase_order_for_quotation: function(frm, warehouse) {
		frappe.call({
			doc: frm.doc,
			method: 'make_purchase_order_for_quotation',
			args: {warehouse: warehouse},
			callback: function(data) {
				if(!data.exc){
					frm.reload_doc();
					frappe.show_alert({
						message: "Purchase Order Created",
						indicator: "green"
					});
					frappe.set_route('List', 'Purchase Order', {
						one_fm_request_for_purchase: frm.doc.name
					})
				}
			},
			freeze: true,
			freeze_message: "Creating Purchase Order"
		})
	},
	make_purchase_order: function(frm) {
		if(frm.is_dirty()){
			frappe.throw(__('Please Save the Document and Continue .!'))
		}
		if(frm.doc.items_to_order.length <= 0){
			frm.scroll_to_field('items_to_order');
			frappe.throw(__("Fill Items to Order to Create Purchase Order"))
		}
		var mandatory_fields_not_set_for_po = frm.doc.items_to_order.filter(items_to_order => (items_to_order.rate <= 0 || !items_to_order.item_code || !items_to_order.supplier));
		var idx_mandatory_fields_not_set_for_po = mandatory_fields_not_set_for_po.map(pt => {return pt.idx}).join(', ');
		if(idx_mandatory_fields_not_set_for_po && idx_mandatory_fields_not_set_for_po.length > 0) {
			frm.scroll_to_field('items_to_order');
			frappe.throw(__("Not able to create PO, Set Item Code/Supplier/Rate in <b>Items to Order</b> rows {0}", [idx_mandatory_fields_not_set_for_po]))
		}

		var items = frm.doc.items_to_order.filter(item => (item.qty_requested && item.qty_requested < item.qty));
		var idx_items = items.map(pt => {return pt.idx}).join(', ');
		if(idx_items && idx_items.length > 0) {
			frm.scroll_to_field('items_to_order');
			frappe.throw(__("Items <b>Items Order</b> are greater in quantity than requested in rows {0}", [idx_items]))
		}

		var stock_item_in_items_to_order = frm.doc.items_to_order.filter(items_to_order => items_to_order.is_stock_item === 1 && !items_to_order.t_warehouse);
		var stock_item_code_in_items_to_order = stock_item_in_items_to_order.map(pt => {return pt.item_code}).join(', ');
		if(stock_item_in_items_to_order && stock_item_in_items_to_order.length > 0 && !frm.doc.warehouse) {
			var d = new frappe.ui.Dialog({
				title: __("Warehouse is mandatory for stock Item {0}", [stock_item_code_in_items_to_order]),
				fields : [{fieldtype: "Link", label: "Warehouse", options: "Warehouse", fieldname: "warehouse", reqd : 1}],
				primary_action_label: __("Create Purchase Order"),
				primary_action: function(){
					frm.events.make_purchase_order_for_quotation(frm, d.get_value('warehouse'));
					d.hide();
				},
			});
			d.show();
		}
		else{
			frm.events.make_purchase_order_for_quotation(frm, false);
		}
	},
	get_requested_items_to_order: function(frm) {
		frm.clear_table('items_to_order');
		frm.doc.items.forEach((item, i) => {
			var items_to_order = frm.add_child('items_to_order');
			items_to_order.item_code = item.item_code
			items_to_order.item_name = item.item_name
			items_to_order.description = item.description
			items_to_order.uom = item.uom
			items_to_order.t_warehouse = item.t_warehouse
			items_to_order.qty_requested = item.qty
			items_to_order.qty = item.qty
			items_to_order.delivery_date = item.schedule_date
			items_to_order.request_for_material = item.request_for_material
		});
		frm.refresh_fields();
	},
	supplier: function(frm) {
		set_supplier_to_items_to_order(frm);
	}
});

var set_intro_related_to_status = function(frm) {
	if (frm.doc.docstatus == 1){
		frm.set_intro(__("Create Request for Quotation (Optional) from the Actions dropdown"), 'yellow');
		frm.set_intro(__("Create Quotation from Supplier (Optional) from the Request for Quotation"), 'yellow');
		frm.set_intro(__("Compare Quotations if Quotaiton Available (Optional) from the Actions dropdown"), 'yellow');
		if((frm.doc.items_to_order && frm.doc.items_to_order.length == 0) || !frm.doc.items_to_order){
			frm.set_intro(__("Fill Items to Order - Check Supplier, Item Code and Rate set Correctly."), 'yellow');
		}
		frm.set_intro(__("Purchase Officer can Create Purchase Order from the Actions dropdown"), 'yellow');
	}
};

var set_supplier_to_items_to_order = function(frm){
	if(frm.doc.items_to_order){
		frm.doc.items_to_order.forEach((item) => {
			frappe.model.set_value(item.doctype, item.name, 'supplier', frm.doc.supplier);
		});
		frm.refresh_field('items_to_order');
	}
};
