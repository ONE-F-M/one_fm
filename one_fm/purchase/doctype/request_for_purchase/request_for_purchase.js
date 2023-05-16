// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request for Purchase', {
	refresh: function(frm) {
		set_intro_related_to_status(frm);
		frm.events.make_custom_buttons(frm);
		if(!frm.doc.approver || (frm.doc.approver != frm.doc.__onload.approver)){
			frm.set_value('approver', frm.doc.__onload.approver);
		}
		if(!frm.doc.accepter || (frm.doc.accepter != frm.doc.__onload.accepter)){
			frm.set_value('accepter', frm.doc.__onload.accepter);
		}
	},
	status: function(frm) {
		if(frm.doc.status && frm.doc.status == 'Rejected'){
			frm.set_df_property('reason_for_rejection', 'reqd', true);
		}
		else{
			frm.set_df_property('reason_for_rejection', 'reqd', false);
		}
	},
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1){
			if(frm.doc.status == 'Draft') {
				if(frm.doc.items.length > frm.doc.items_to_order.length && !frm.doc.notified_the_rfm_requester){
					frm.add_custom_button(__("Notify the Requester"),
						() => frm.events.notify_the_rfm_requester(frm));
				}
				frm.add_custom_button(__("Request for Quotation"),
					() => frm.events.make_request_for_quotation(frm), __('Create'));

				frm.add_custom_button(__("Compare Quotations"),
					() => frm.events.make_quotation_comparison_sheet(frm));
			}
			if(frm.doc.status == 'Approved'){
				frm.add_custom_button(__("Purchase Order"),
					() => frm.events.make_purchase_order(frm), __('Create'));
			}
		}
		if (frm.doc.docstatus == 1){
			if(frappe.session.user==frm.doc.owner && frm.doc.status == "Draft" && frm.doc.items_to_order && frm.doc.items_to_order.length > 0){
				// Changed from "Send request" while removing authorizations and approvals.
				frm.add_custom_button(__('Confirm Item Details and Send for Approval'), () => frm.events.accept_approve_reject_request_for_purchase(frm, "Draft Request", false)).addClass('btn-primary');
			}
			if("accepter" in frm.doc.__onload && frappe.session.user==frm.doc.__onload.accepter && frm.doc.status == "Draft"){
				frm.add_custom_button(__('Accept'), () => frm.events.accept_approve_reject_request_for_purchase(frm, "Accepted", false)).addClass('btn-primary');
				frm.add_custom_button(__('Reject'), () => frm.events.reject_request_for_purchase(frm, 'Rejected')).addClass('btn-danger');
			}
			if("approver" in frm.doc.__onload && frappe.session.user==frm.doc.__onload.approver && ["Accepted", "Draft Request"].includes(frm.doc.status)){
				frm.add_custom_button(__('Approve'), () => frm.events.accept_approve_reject_request_for_purchase(frm, "Approved", false)).addClass('btn-primary');
				frm.add_custom_button(__('Reject'), () => frm.events.reject_request_for_purchase(frm, 'Rejected')).addClass('btn-danger');
			}
		}
	},
	reject_request_for_purchase: function(frm, status) {
		var d = new frappe.ui.Dialog({
			title : __("Reject Request for Purchase"),
			fields : [{
				fieldtype: "Small Text",
				label: "Reason for Rejection",
				fieldname: "reason_for_rejection",
				reqd : 1
			}],
			primary_action_label: __("Reject"),
			primary_action: function(){
				frm.events.accept_approve_reject_request_for_purchase(frm, status, d.get_value('reason_for_rejection'));
				d.hide();
			},
		});
		d.show();
	},
	accept_approve_reject_request_for_purchase: function(frm, status, reason_for_rejection) {
		frappe.call({
			doc: frm.doc,
			method: 'accept_approve_reject_request_for_purchase',
			args: {
				status: status,
				accepter: frm.doc.__onload.accepter,
				approver: frm.doc.__onload.approver,
				reason_for_rejection: reason_for_rejection
			},
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
			freeze: true
		});
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
				}
			},
			freeze: true,
			freeze_message: "Creating Purchase Order"
		})
	},
	make_purchase_order: function(frm) {
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
	if(frm.doc.docstatus == 0){
		frm.set_intro("")
		frm.set_intro(__("Submit the document to confirm and notify the Purchase Manager"), 'blue');
	}
	if (frm.doc.docstatus == 1){
		if(frm.doc.status == 'Draft') {
			frm.set_intro(__("Create Request for Quotation (Optional)."), 'yellow');
			frm.set_intro(__("Compare Quotations if Quotaiton Available (Optional)."), 'yellow');
			if((frm.doc.items_to_order && frm.doc.items_to_order.length == 0) || !frm.doc.items_to_order){
				frm.set_intro(__("Fill Items to Order - Check Supplier and Item Code set Correctly."), 'yellow');
			}
			frm.set_intro(__("Click `Confirm Item Details and Send for Approval` Button"), 'yellow');
			frm.set_intro(__("On Approval, Requester can create PO from the create dropdown button"), 'yellow');
		}
		if(frm.doc.status == "Draft Request"){
			frm.set_intro(__("On Accept notify Approver"), 'yellow');
			frm.set_intro(__("On Approval, Requester can create PO from the create dropdown button"), 'yellow');
		}
		if(frm.doc.status == "Accepted"){
			frm.set_intro(__("On Approval, Requester can create PO from the create dropdown button"), 'yellow');
		}
		if(frm.doc.status == 'Approved'){
			frappe.db.get_value("Purchase Order", {"one_fm_request_for_purchase": frm.doc.name}, "name", function(r) {
				if(!r || !r.name){
					frm.set_intro(__("Requester can create PO"), 'yellow');
				}
			})
		}
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
