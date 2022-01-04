// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

// eslint-disable-next-line
{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on('Request for Material', {
	setup: function(frm) {
		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.ordered_qty) ? "green" : "orange"; });

		frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			};
		});
		if(frm.doc.docstatus==1 && frappe.session.user==frm.doc.request_for_material_approver && frm.doc.status!='Approved'){
			var df = frappe.meta.get_docfield("Request for Material Item","reject_item", cur_frm.doc.name);
            df.hidden = 0;
		}
	},
	onload: function(frm) {
		erpnext.utils.add_item(frm);
		if(!frm.doc.requested_by){
			frm.set_value('requested_by', frappe.session.user);
		}

		// set schedule_date
		set_schedule_date(frm);
		frm.fields_dict["items"].grid.get_field("t_warehouse").get_query = function(doc) {
			return {
				filters: {'company': doc.company}
			};
		};

	},
	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},
	refresh: function(frm) {
		frm.events.make_custom_buttons(frm);
		set_item_field_property(frm);
		let status = ['Draft', 'Accepted', 'Approved', 'Rejected', 'Transferred'];
		if(status.includes(frm.doc.status) && frm.doc.docstatus == 1){
			frm.set_df_property('status', 'options', status);
		}
		if(frm.doc.docstatus == 0){
			if (frappe.user.has_role("Stock User")){
				frm.set_df_property('type', 'options', "\nIndividual\nDepartment\nStock\nProject\nOnboarding");
			}
			else{
				frm.set_df_property('type', 'options', "\nIndividual\nDepartment\nProject\nOnboarding");
			}
		}
		if(frm.is_new()){
			frappe.db.get_value('Stock Settings', '', 'default_warehouse', function(r) {
				if(r && r.default_warehouse){
					frm.set_value('t_warehouse', r.default_warehouse);
				}
				else{
					frm.set_value('t_warehouse', '');
				}
			});
		}
		set_filters(frm);
		set_warehouse_filters(frm);
	},
	// after_save: function(frm){
	// 	let item_changes =
	// 	frm.doc.items.forEach((item, i) => {
	// 		if(item.remarks){
	// 			notify_changes_to_requester(item.remarks)
	// 		}
	// 	});
	// },
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status == 'Approved' && frappe.user.has_role("Stock User")) {
			// console.log(frm.doc.items[0].actual_qty);
			// console.log(frm.doc.items[0].actual_qty-frm.doc.items[0].qty);
			if(frm.doc.items){
				var any_items_ordered = false;
				var item_exist_in_stock = false;
				var purchase_item_exist = false;

				if(frm.doc.per_ordered>0){
					any_items_ordered = true;
				}
				frm.doc.items.forEach((item, i) => {
					if(item.item_code && item.actual_qty>0){
						item_exist_in_stock = true;
					}
					if(item.pur_qty > 0){
						purchase_item_exist = true;
					}
					// else{
					// 	frappe.msgprint(__("Warning: Requested Qty exceeds Qty in warehouse"));
					// }
				});

				if(item_exist_in_stock){
					if(frm.doc.type=="Individual" || frm.doc.type=="Onboarding" || frm.doc.type=="Project"|| frm.doc.type=="Project Mobilization" || frm.doc.type=="Stock"){
						frappe.db.get_value('Stock Entry', {'one_fm_request_for_material': frm.doc.name}, ['name', 'docstatus'],function(r) {
							if(r && r.name && r.docstatus != 2){
								frappe.show_alert({
									message:__('A Material Transfer ')+r.name+__(' has been made against this RFM'),
									indicator:'green'
								}, 5);
							}
							else{
								if(r && r.docstatus == 2){
									frappe.show_alert({
										message:__('A Material Transfer')+r.name+__(' was made against this RFM, which has now been cancelled'),
										indicator:'red'
									}, 5);
								}
								if (frm.doc.type=="Stock"){
									frm.add_custom_button(__("Material Transfer"),
									    () => frm.events.make_stock_entry(frm), __('Create'));
								}else{
									frm.add_custom_button(__("Material Transfer"),//changed from Issue to transfer temporarily
									    () => frm.events.make_stock_entry_issue(frm), __('Create'));
								}

							}
						});
						frm.add_custom_button(__("Sales Invoice"),
							() => frm.events.make_sales_invoice(frm), __('Create'));
						if(purchase_item_exist){
							frappe.db.get_value('Request for Purchase', {'request_for_material': frm.doc.name}, ['name','docstatus'],function(r) {
								if(r && r.name && r.docstatus != 2){
									frappe.show_alert({
										message:__('A purchase request ')+r.name+__(' has been made against this RFM'),
										indicator:'green'
									}, 5);
								}
								else{
									if(r && r.docstatus == 2){
										frappe.show_alert({
											message:__('Request for Purchase ')+r.name+__(' was made against this RFM, which has now been cancelled'),
											indicator:'red'
										}, 5);
									}
									frm.add_custom_button(__("Request for Purchase"),
							            () => frm.events.make_request_for_purchase(frm), __('Create'));
								}
							});

						}
						if(any_items_ordered){
							frm.add_custom_button(__("Make Delivery Note"),
						 	    () => frm.events.make_delivery_note(frm), __('Create'));
						}

					}
					// else if (frm.doc.type=="Stock"){
					// 	frm.add_custom_button(__("Transfer Material"),
					// 		() => frm.events.make_stock_entry(frm), __('Create'));
					// 	frm.add_custom_button(__("Sales Invoice"),
					// 		() => frm.events.make_sales_invoice(frm), __('Create'));
					// 	// frm.add_custom_button(__("Make Delivery Note"),
					// 	// 	() => frm.events.make_delivery_note(frm), __('Create'));
					// }

				}
				else {
					//Needs further dicussion with Jamsheer
					frm.add_custom_button(__("Sales Invoice"),
					    () => frm.events.make_sales_invoice(frm), __('Create'));
					frappe.db.get_value('Request for Purchase', {'request_for_material': frm.doc.name}, ['name','docstatus'],function(r) {
						if(r && r.name && r.docstatus != 2){
							frappe.show_alert({
								message:__('A purchase request ')+r.name+__(' has been made against this RFM'),
								indicator:'green'
							}, 5);
						}
						else{
							if(r && r.docstatus == 2){
								frappe.show_alert({
									message:__('Request for Purchase ')+r.name+__(' was made against this RFM, which has now been cancelled'),
									indicator:'red'
								}, 5);
							}
							frm.add_custom_button(__("Request for Purchase"),
								() => frm.events.make_request_for_purchase(frm), __('Create'));
						}
					});
					if(any_items_ordered){
						frm.add_custom_button(__("Make Delivery Note"),
							() => frm.events.make_delivery_note(frm), __('Create'));
					}
				}
			}

			frm.page.set_inner_btn_group_as_primary(__('Create'));

			// stop
			// frm.add_custom_button(__('Stop'),
			// 	() => frm.events.update_status(frm, 'Stopped'));
		}

		// if (frm.doc.docstatus == 1 && frm.doc.status == 'Stopped') {
		// 	frm.add_custom_button(__('Re-open'), () => frm.events.update_status(frm, 'Submitted'));
		// }

		if (frm.doc.docstatus == 1){
			// if(frappe.session.user==frm.doc.request_for_material_accepter && frm.doc.status == "Draft"){
			// 	frm.add_custom_button(__('Accept'), () => frm.events.confirm_accept_approve_request_for_material(frm, 'Accepted')).addClass('btn-primary');
			// 	frm.add_custom_button(__('Reject'), () => frm.events.reject_request_for_material(frm, 'Rejected')).addClass('btn-danger');
			// }
			if(frappe.session.user==frm.doc.request_for_material_approver && (frm.doc.status == "Accepted" || frm.doc.status == "Draft")){
				frm.add_custom_button(__('Approve'), () => frm.events.confirm_accept_approve_request_for_material(frm, 'Approved')).addClass('btn-primary');
				frm.add_custom_button(__('Reject'), () => frm.events.reject_request_for_material(frm, 'Rejected')).addClass('btn-danger');
			}
		}
	},
	// designation: function(frm) {
	// 	fetch_designation_items(frm);
	// },
	erf: function(frm) {
		fetch_erf_items(frm);
	},

	reject_request_for_material: function(frm, status) {
		var d = new frappe.ui.Dialog({
			title : __("Reject Request for Material"),
			fields : [{
				fieldtype: "Small Text",
				label: "Reason for Rejection",
				fieldname: "reason_for_rejection",
				reqd : 1
			}],
			primary_action_label: __("Reject"),
			primary_action: function(){
				frm.events.accept_approve_reject_request_for_material(frm, status, d.get_value('reason_for_rejection'));
				d.hide();
			},
		});
		d.show();
	},
	confirm_accept_approve_request_for_material: function(frm, status) {
		let msg_status = 'Approve';
		if(status != 'Approved'){
			msg_status = status == 'Accepted' ? 'Accept': 'Reject'
		}
		frappe.confirm(
			__('Do You Want to {0} this Request for Material', [msg_status]),
			function(){
				// Yes
				frm.events.accept_approve_reject_request_for_material(frm, status, false);
			},
			function(){} // No
		);
	},
	accept_approve_reject_request_for_material: function(frm, status, reason_for_rejection) {
		frappe.call({
			doc: frm.doc,
			method: 'accept_approve_reject_request_for_material',
			args: {status: status, reason_for_rejection: reason_for_rejection},
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
			freeze: true,
			freeze_message: __('Updating the Request..!')
		});
	},
	update_status: function(frm, stop_status) {
		frappe.call({
			method: 'erpnext.stock.doctype.material_request.material_request.update_status',
			args: { name: frm.doc.name, status: stop_status },
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			}
		});
	},


	get_item_data: function(frm, item) {
		if (!item.item_code) return;
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse,
					doctype: frm.doc.doctype,
					buying_price_list: frappe.defaults.get_default('buying_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					name: frm.doc.name,
					qty: item.qty || 1,
					stock_qty: item.stock_qty,
					company: frm.doc.company,
					conversion_rate: 1,
					material_request_type: frm.doc.material_request_type,
					plc_conversion_rate: 1,
					rate: item.rate,
					conversion_factor: item.conversion_factor
				}
			},
			callback: function(r) {
				const d = item;
				//console.log(r.message);
				//console.log(r.message.warehouse);
				if(!r.exc) {
					$.each(r.message, function(k, v) {
						if(!d[k]) d[k] = v;
						if(d.qty>d.actual_qty){
							d.pur_qty = d.qty-d.actual_qty
							d.quantity_to_transfer = d.actual_qty
						} else if(d.qty<d.actual_qty){
							d.pur_qty = 0
							d.quantity_to_transfer = d.qty
						}
					});
				}
			}
		});
	},
	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},
	make_delivery_note: function(frm) {
		if(frm.is_dirty()){
			frappe.msgprint(__("Please Update the Document and Create."))
		}
		else{
			frappe.model.open_mapped_doc({
				method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_delivery_note",
				frm: frm
			});
		}
	},
	make_request_for_purchase: function(frm) {
		if(frm.is_dirty()){
			frappe.msgprint(__("Please Update the Document and Create."))
		}
		else{
			frappe.model.open_mapped_doc({
				method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_request_for_purchase",
				frm: frm
			});
		}
	},
	make_stock_entry: function(frm) {
		if(frm.is_dirty()){
			frappe.msgprint(__("Please Update the Document and Create."))
		}
		else{
			frappe.model.open_mapped_doc({
				method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_stock_entry",
				frm: frm
			});
		}
	},
	make_stock_entry_issue: function(frm) {
		if(frm.is_dirty()){
			frappe.msgprint(__("Please Update the Document and Create."))
		}
		else{
			frappe.model.open_mapped_doc({
				method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_stock_entry_issue",
				frm: frm
			});
		}
	},
	make_sales_invoice: function(frm) {
		if(frm.is_dirty()){
			frappe.msgprint(__("Please Update the Document and Create."))
		}
		else{
			frappe.model.open_mapped_doc({
				method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_sales_invoice",
				frm: frm
			});
		}
	},
	t_warehouse: function(frm) {
		set_t_warehouse(frm);
	},
	status: function(frm) {
		if(frm.doc.status && frm.doc.status == 'Rejected'){
			frm.set_df_property('reason_for_rejection', 'reqd', true);
		}
		else{
			frm.set_df_property('reason_for_rejection', 'reqd', false);
		}
	},
	type: function(frm) {
		set_employee_or_project(frm);
		set_item_field_property(frm);
		set_warehouse_filters(frm);
	},
	project: function(frm) {
		set_warehouse_filters(frm);
	},
	department: function(frm) {
		set_warehouse_filters(frm);
	},
	site: function(frm) {
		set_warehouse_filters(frm);
	}
});

var set_filters = function(frm) {
	frm.set_query("project", function() {
		return {
			filters: [
				['customer', '=', frm.doc.customer]
			]
		};
	});
	frm.set_query("site", function() {
		return {
			filters: [
				['project', '=', frm.doc.project]
			]
		};
	});
	frm.set_query("t_warehouse", function() {
		return {
			filters: {'is_group': 0}
		};
	});
};


var fetch_designation_items = function(frm) {
	if(frm.doc.designation){
		frappe.call({
			method: 'one_fm.purchase.doctype.request_for_material.request_for_material.bring_designation_items',
			args: {'designation': frm.doc.designation},
			callback: function(r) {
				if(r.message){
					var designation = r.message;
					//console.log(designation.item_list);
					if(designation.item_list && designation.item_list.length > 0){
						//console.log("Quantity", designation.item_list[0].item_name);
						frm.get_field("items").grid.grid_rows[0].remove();
						for ( var i=0; i< designation.item_list.length; i++ ){
							//console.log("here");
							let d = frm.add_child("items", {
								requested_item_name: designation.item_list[i].item_name,
								requested_description: "None",
								qty: designation.item_list[i].quantity,
								uom: designation.item_list[i].uom
							});
							/*console.log(d)
						    var item = designation.item_list[i];
							console.log("Getting",item)
							for ( var key in  item) {
								if ( !is_null(item[key]) ) {
									d[key] = item[key];
								}
							}*/
						}
						frm.refresh_field("items");
						//var extracted_designation_item_list=designation.item_list[0];
						//console.log("This",extracted_designation_item_list)
						//frm.set_value('items', designation.item_list[0]);
					}
				}
			},
			freeze: true,
			freeze_message: __('Fetching Data from Project to Set Default Data')
		});
	}
};

var fetch_erf_items = function(frm){
	if(frm.doc.erf){
		frappe.call({
			method: 'one_fm.purchase.doctype.request_for_material.request_for_material.bring_erf_items',
			args: {'erf': frm.doc.erf},
			callback: function(r) {
				if(r.message){
					var erf = r.message;
					if(erf.item_list && erf.item_list.length > 0){
						frm.get_field("items").grid.grid_rows[0].remove();
						for ( var i=0; i< erf.item_list.length; i++ ){
							let d = frm.add_child("items", {
								requested_item_name: erf.item_list[i].item_name,
								requested_description: erf.item_list[i].description,
								qty: erf.item_list[i].quantity,
								uom: erf.item_list[i].uom
							});
						}
						frm.refresh_field("items");
					}
					else if (erf.item_list.length <= 0){
						frappe.msgprint(__("No items found in this erf."))
					}
				}
			},
			freeze: true,
			freeze_message: __('Fetching Data from ERF to Set Default Data')
		});
	}
};

var set_item_field_property = function(frm) {
	if((frm.doc.docstatus == 1 && frappe.session.user == frm.doc.request_for_material_accepter) || frm.doc.type == 'Stock'){
		var df = frappe.meta.get_docfield("Request for Material Item", "item_code", frm.doc.name);
		df.read_only = false;
	}
	else if((frm.doc.docstatus == 1 && frm.doc.status == 'Approved') || frm.doc.type == 'Stock'){
		frappe.meta.get_docfield("Request for Material Item", "item_code", frm.doc.name).read_only = false;
	}
	if(frm.doc.type == 'Stock'){
		frappe.meta.get_docfield("Request for Material Item", "requested_item_name", frm.doc.name).read_only = true;
		frappe.meta.get_docfield("Request for Material Item", "requested_item_name", frm.doc.name).reqd = false;
		frappe.meta.get_docfield("Request for Material Item", "requested_description", frm.doc.name).read_only = true;
		frappe.meta.get_docfield("Request for Material Item", "requested_description", frm.doc.name).reqd = false;
	}
	else{
		frappe.meta.get_docfield("Request for Material Item", "requested_item_name", frm.doc.name).read_only = false;
		frappe.meta.get_docfield("Request for Material Item", "requested_item_name", frm.doc.name).reqd = true;
		frappe.meta.get_docfield("Request for Material Item", "requested_description", frm.doc.name).read_only = false;
		frappe.meta.get_docfield("Request for Material Item", "requested_description", frm.doc.name).reqd = true;
	}
};

var set_warehouse_filters = function(frm) {
	var wh_filters = {'is_group': 0};
	if(frm.doc.type == 'Individual' || frm.doc.type == 'Department'){
		wh_filters = {'is_group': 0, 'department': frm.doc.department};
	}
	if(frm.doc.type == 'Project'){
		wh_filters = {'is_group': 0, 'one_fm_project': frm.doc.project, 'one_fm_site': frm.doc.site};
	}
	frm.set_query("t_warehouse", function() {
		return {
			filters: wh_filters
		};
	});
}

var set_employee_or_project = function(frm) {
	if(frm.doc.type){
		frm.set_df_property('department', 'read_only', true);
		if(frm.doc.type=='Individual'){
			frm.set_df_property('employee', 'reqd', true);
			frm.set_df_property('project', 'reqd', false);
			frm.set_df_property('department', 'reqd', false);
			frm.set_df_property('department', 'read_only', false);
			frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'name', function(r) {
				if(r && r.name){
					frm.set_value('employee', r.name);
				}
				else{
					frappe.throw(__('Employee or Employee email not created for current user'))
				}
			});
		}
		else if(frm.doc.type=='Department'){
			frm.set_df_property('employee', 'reqd', false);
			frm.set_df_property('department', 'reqd', true);
			frm.set_df_property('department', 'read_only', false);
			frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'name', function(r) {
				if(r && r.name){
					frm.set_value('employee', r.name);
				}
				else{
					frappe.throw(__('Employee or Employee email not created for current user'))
				}
			});
		}
		else if(frm.doc.type=='Project'|| frm.doc.type=='Project Mobilization'){
			frm.set_df_property('project', 'reqd', true);
			frm.set_df_property('department', 'reqd', false);
			frm.set_df_property('department', 'read_only', false);
			frm.set_df_property('customer', 'reqd', (frm.doc.type=='Project')?true:false);
			frm.set_df_property('site', 'reqd', (frm.doc.type=='Project')?true:false);
		}
		else if(frm.doc.type=='Onboarding'){
			frm.set_df_property('erf', 'reqd', true);
		}
		else if(frm.doc.type=='Stock'){
			frm.set_df_property('department', 'reqd', false);
			frm.set_df_property('department', 'read_only', false);
			frm.set_df_property('project', 'reqd', false);
		}
	}


	// else if(frm.doc.type){
	// 	frm.set_df_property('employee', 'reqd', (frm.doc.type=='Individual')?true:false);
	//	frm.set_df_property('project', 'reqd', (frm.doc.type=='Project Mobilization')?true:false);
	// 	frm.set_df_property('project', 'reqd', (frm.doc.type=='Project')?true:false);
	// 	frm.set_df_property('project', 'reqd', (frm.doc.type=='Onboarding')?true:false);
	// 	if(frm.doc.type=='Individual'){
	// 		frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'employee_name', function(r) {
	// 			if(r && r.employee_name){
	// 				frm.set_value('employee', r.employee_name);
	// 			}
	// 			else{
	// 				frappe.throw(__('Employee or Employee email not created for current user'))
	// 			}
	// 		});
	// 	}
	// }
	else{
		frm.set_df_property('employee', 'reqd', false);
		frm.set_df_property('project', 'reqd', false);
		frm.set_value('employee', '');
		frm.set_value('department', '');
		frm.set_value('employee_name', '');
		frm.set_value('project', '');
	}
};


frappe.ui.form.on("Request for Material Item", {
	// refresh: function (frm){
	// 	if(frm.doc.docstatus == 1 && frm.doc.status == 'Approved'){
	// 		frm.set_df_property('item_code', 'read_only', false);
	//     }
	// },
	qty: function (frm, doctype, name) {
		// var d = locals[doctype][name];
		// if ((flt(d.quantity_to_transfer)+flt(d.pur_qty)) > (flt(d.qty))) {
		// 	frappe.msgprint(__("Warning: Cannot exceed total Material Requested Qty"));
		// }
		//
		// const item = locals[doctype][name];
		// frm.events.get_item_data(frm, item);
	},
	pur_qty: function (frm, doctype, name){
		var d = locals[doctype][name];
		console.log("Hello"+d.quantity_to_transfer)
		if (d.quantity_to_transfer > (d.qty+d.pur_qty) || d.quantity_to_transfer > (d.qty+d.pur_qty)){
			d.quantity_to_transfer = d.qty-d.pur_qty
			console.log(d.quantity_to_transfer)
		}
		if ((flt(d.quantity_to_transfer)+flt(d.pur_qty)) > (flt(d.qty))) {
			frappe.msgprint(__("Warning: Cannot exceed total Material Requested Qty"));
		}


	},
	quantity_to_transfer: function (frm, doctype, name){
		var d = locals[doctype][name];
		if ((flt(d.quantity_to_transfer)+flt(d.pur_qty)) > (flt(d.qty))) {
			frappe.msgprint(__("Warning: Cannot exceed total Material Requested Qty"));
		}

	},

	rate: function(frm, doctype, name) {
		// const item = locals[doctype][name];
		// frm.events.get_item_data(frm, item);
	},

	item_code: function(frm, doctype, name) {
		const item = locals[doctype][name];
		item.rate = 0;
		set_schedule_date(frm);
		if(!item.item_code){
			frappe.model.set_value(item.doctype, item.name, 'item_name', '');
		}
		frm.events.get_item_data(frm, item);
		// if(item.qty>item.actual_qty){}
	},

	schedule_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if(!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	}
});

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	tc_name: function() {
		this.get_terms();
	},

	item_code: function() {
		// to override item code trigger from transaction.js
	},

	validate_company_and_party: function() {
		return true;
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	validate: function() {
		set_schedule_date(this.frm);
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(!row.uom){
			this.frm.script_manager.copy_from_first_row("items", row, ["uom"]);
		}
		if(doc.schedule_date) {
			row.schedule_date = doc.schedule_date;
			refresh_field("schedule_date", cdn, "items");
		} else {
			this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
			this.frm.script_manager.copy_from_first_row("items", row, ["t_warehouse"]);
		}
	},

	items_on_form_rendered: function() {
		set_schedule_date(this.frm);
	},

	schedule_date: function() {
		set_schedule_date(this.frm);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
	}
};

function set_t_warehouse(frm){
	if(frm.doc.t_warehouse){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "t_warehouse");
	}
};
