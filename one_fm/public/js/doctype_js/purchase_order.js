frappe.ui.form.on('Purchase Order', {
	setup: function(frm) {
		if(frappe.user.has_role("Purchase User")){
			frm.set_df_property('quoted_delivery_date', 'hidden', 0);
		} else {
			frm.set_df_property('quoted_delivery_date', 'hidden', 1);
		}
		// frm.set_df_property('quoted_delivery_date', 'hidden', (frm.doc.docstatus==1 && frappe.user.has_role("Purchase User"))?false:true);
	},
	refresh: function(frm) {
		hide_tax_fields(frm);
		hide_subscription_section(frm);
		set_field_property_for_documents(frm);
		set_field_property_for_other_documents(frm);
	},

	set_warehouse: function(frm){
		if(frm.doc.set_warehouse){
			frappe.call({
				method: 'one_fm.purchase.utils.get_warehouse_contact_details',
				args: {'warehouse': frm.doc.set_warehouse},
				callback: function(r) {
					var contact = r.message;
					if(contact){
						if(contact[0]){
							frm.set_value('one_fm_warehouse_contact_person', contact[0].contact_display);
							frm.set_value('one_fm_contact_person_email', contact[0].contact_email);
							frm.set_value('one_fm_contact_person_phone', contact[0].contact_mobile);
						}
						frm.set_value('one_fm_warehouse_location', contact[1]);
					}
				}
			});
		}
	},
	one_fm_type_of_purchase: function(frm) {
		set_field_property_for_documents(frm);
	},
	one_fm_other_documents_required: function(frm) {
		set_field_property_for_other_documents(frm);
	}
});

var set_field_property_for_other_documents = function(frm) {
	if(frm.doc.one_fm_other_documents_required && frm.doc.one_fm_other_documents_required == 'Yes'){
		frm.set_df_property('one_fm_details_of_other_documents', 'reqd', true);
	}
	else{
		frm.set_df_property('one_fm_details_of_other_documents', 'reqd', false);
		if(frm.doc.one_fm_details_of_other_documents){
			frm.set_value('one_fm_details_of_other_documents', '');
		}
	}
};

var set_field_property_for_documents = function(frm) {
	if(frm.doc.one_fm_type_of_purchase && frm.doc.one_fm_type_of_purchase == "Import"){
		frm.set_df_property('one_fm_certificate_of_origin_required', 'reqd', true);
		frm.set_df_property('one_fm_other_documents_required', 'reqd', true);
	}
	else{
		frm.set_df_property('one_fm_certificate_of_origin_required', 'reqd', false);
		frm.set_df_property('one_fm_other_documents_required', 'reqd', false);
		if(frm.doc.one_fm_certificate_of_origin_required){
			frm.set_value('one_fm_certificate_of_origin_required', '');
		}
		if(frm.doc.one_fm_other_documents_required == 'Yes'){
			frm.set_value('one_fm_other_documents_required', '');
		}
	}
};

var hide_tax_fields = function(frm) {
	let field_list = ['tax_category', 'section_break_52', 'taxes_and_charges', 'taxes', 'sec_tax_breakup', 'totals'];
	field_list.forEach((field, i) => {
		frm.set_df_property(field, 'hidden', true);
	});
};

var hide_subscription_section = function(frm) {
	frm.set_df_property('subscription_section', 'hidden', true);
};

frappe.ui.form.on('Payment Schedule', {
	refresh(frm) {
		// your code here
	},
	payment_term: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.payment_term == 'Purchase Receipt based') {
		    console.log("here")
			frm.set_df_property('payment_schedule', 'read_only', true);
		}
		else{
			frm.set_df_property('payment_schedule', 'read_only', false);
		}
	}
})


// class MyPurchaseOrderController extends erpnext.buying.PurchaseOrderController {
// 	constructor(frm) {
// 	  super(frm);
// 	  this.frm = frm;
// 	}
  
// 	refresh() {
// 	  super.refresh(this.frm.doc);
  
// 	  console.log(333333333)
// 	  this.frm.page.set_inner_btn_group_as_primary(__('Create'));
// 	  this.frm.remove_custom_button('Purchase Receipt');
// 	//   this.frm.page.clear_inner_toolbar();
	  
// 	}
//   }

//   frappe.ui.form.on('Purchase Order', {
// 	refresh: function(frm) {
// 		frm.controller = new MyPurchaseOrderController(frm);
// 		frm.controller.refresh();
// 	}
// });






// frappe.provide("erpnext.buying");

// erpnext.buying.PurchaseOrderController = class PurchaseOrderController extends erpnext.buying.BuyingController {
// 	setup() {
// 		this.frm.custom_make_buttons = {
// 			'Purchase Receipt': 'Purchase Receipt',
// 			'Purchase Invoice': 'Purchase Invoice',
// 			'Payment Entry': 'Payment',
// 			'Subcontracting Order': 'Subcontracting Order',
// 			'Stock Entry': 'Material to Supplier'
// 		}

// 		super.setup();
// 	}

// 	refresh(doc, cdt, cdn) {
// 		var me = this;
// 		super.refresh();
// 		var allow_receipt = false;
// 		var is_drop_ship = false;

// 		for (var i in cur_frm.doc.items) {
// 			var item = cur_frm.doc.items[i];
// 			if(item.delivered_by_supplier !== 1) {
// 				allow_receipt = true;
// 			} else {
// 				is_drop_ship = true;
// 			}

// 			if(is_drop_ship && allow_receipt) {
// 				break;
// 			}
// 		}

// 		this.frm.set_df_property("drop_ship", "hidden", !is_drop_ship);

// 		if(doc.docstatus == 1) {
// 			this.frm.fields_dict.items_section.wrapper.addClass("hide-border");
// 			if(!this.frm.doc.set_warehouse) {
// 				this.frm.fields_dict.items_section.wrapper.removeClass("hide-border");
// 			}

// 			if(!in_list(["Closed", "Delivered"], doc.status)) {
// 				if(this.frm.doc.status !== 'Closed' && flt(this.frm.doc.per_received) < 100 && flt(this.frm.doc.per_billed) < 100) {
// 					// Don't add Update Items button if the PO is following the new subcontracting flow.
// 					if (!(this.frm.doc.is_subcontracted && !this.frm.doc.is_old_subcontracting_flow)) {
// 						this.frm.add_custom_button(__('Update Items'), () => {
// 							erpnext.utils.update_child_items({
// 								frm: this.frm,
// 								child_docname: "items",
// 								child_doctype: "Purchase Order Detail",
// 								cannot_add_row: false,
// 							})
// 						});
// 					}
// 				}
// 				if (this.frm.has_perm("submit")) {
// 					if(flt(doc.per_billed, 6) < 100 || flt(doc.per_received, 6) < 100) {
// 						if (doc.status != "On Hold") {
// 							this.frm.add_custom_button(__('Hold'), () => this.hold_purchase_order(), __("Status"));
// 						} else{
// 							this.frm.add_custom_button(__('Resume'), () => this.unhold_purchase_order(), __("Status"));
// 						}
// 						this.frm.add_custom_button(__('Close'), () => this.close_purchase_order(), __("Status"));
// 					}
// 				}

// 				if(is_drop_ship && doc.status!="Delivered") {
// 					this.frm.add_custom_button(__('Delivered'),
// 						this.delivered_by_supplier, __("Status"));

// 					this.frm.page.set_inner_btn_group_as_primary(__("Status"));
// 				}
// 			} else if(in_list(["Closed", "Delivered"], doc.status)) {
// 				if (this.frm.has_perm("submit")) {
// 					this.frm.add_custom_button(__('Re-open'), () => this.unclose_purchase_order(), __("Status"));
// 				}
// 			}
// 			if(doc.status != "Closed") {
// 				if (doc.status != "On Hold") {
// 					if(flt(doc.per_received) < 100 && allow_receipt) {
// 						// cur_frm.add_custom_button(__('Purchase Receipt'), this.make_purchase_receipt, __('Create'));
// 						if (doc.is_subcontracted) {
// 							if (doc.is_old_subcontracting_flow) {
// 								if (me.has_unsupplied_items()) {
// 									cur_frm.add_custom_button(__('Material to Supplier'), function() { me.make_stock_entry(); }, __("Transfer"));
// 								}
// 							}
// 							else {
// 								cur_frm.add_custom_button(__('Subcontracting Order'), this.make_subcontracting_order, __('Create'));
// 							}
// 						}
// 					}
// 					if(flt(doc.per_billed) < 100)
// 						cur_frm.add_custom_button(__('Purchase Invoice'),
// 							this.make_purchase_invoice, __('Create'));

// 					if(flt(doc.per_billed) < 100 && doc.status != "Delivered") {
// 						cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_payment_entry, __('Create'));
// 					}

// 					if(flt(doc.per_billed) < 100) {
// 						this.frm.add_custom_button(__('Payment Request'),
// 							function() { me.make_payment_request() }, __('Create'));
// 					}

// 					if(!doc.auto_repeat) {
// 						cur_frm.add_custom_button(__('Subscription'), function() {
// 							erpnext.utils.make_subscription(doc.doctype, doc.name)
// 						}, __('Create'))
// 					}

// 					if (doc.docstatus === 1 && !doc.inter_company_order_reference) {
// 						let me = this;
// 						let internal = me.frm.doc.is_internal_supplier;
// 						if (internal) {
// 							let button_label = (me.frm.doc.company === me.frm.doc.represents_company) ? "Internal Sales Order" :
// 								"Inter Company Sales Order";

// 							me.frm.add_custom_button(button_label, function() {
// 								me.make_inter_company_order(me.frm);
// 							}, __('Create'));
// 						}

// 					}
// 				}

// 				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
// 			}
// 		} else if(doc.docstatus===0) {
// 			cur_frm.cscript.add_from_mappers();
// 		}
// 	}
	
//     // ...

//     make_packing_slip() {
//         // ...
//     }

// 	make_purchase_receipt() {
// 		console.log("44444444444444444444444444");
// 		frappe.model.open_mapped_doc({
// 			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
// 			frm: cur_frm,
// 			freeze_message: __("Creating Purchase Receipt ...")
// 		})
// 	}

//     // ...

//     make_payment_request() {
//         // ...
//     }
// }

$.extend(cur_frm.cscript, new erpnext.buying.PurchaseOrderController({frm: cur_frm}));

