// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

// eslint-disable-next-line
frappe.provide("erpnext.accounts.dimensions");
erpnext.buying.setup_buying_controller();

frappe.ui.form.on('Request for Material', {
	purchase_rfm: function(frm){
		if(frm.is_dirty()){
			frappe.msgprint(__('Please save before creating Purchase RFM.'));
			return;
		}
		if(frm.doc.linked_request_for_material){
			frappe.msgprint(__('This document is already a Purchase RFM.'));
			return;
		}
		if(!frm.doc.linked_request_for_material) {
			frappe.call({
				doc: frm.doc,
				method: 'get_session_user_approver',
				callback: function(r) {
					let new_doc = frappe.model.copy_doc(frm.doc);
					new_doc.linked_request_for_material = frm.doc.name;
					new_doc.workflow_state = '';
					new_doc.linked_purchase_rfm = ""
					new_doc.issue_transfer_rfm =  frm.doc.name
					new_doc.purpose = 'Purchase';
					new_doc.requested_by = frappe.session.user;
					new_doc.request_for_material_approver = r.message;
					new_doc.docstatus = 0;
					for(let i=0; i<new_doc.items.length; i++){
						new_doc.items[i].linked_request_for_material = frm.doc.name
					}
					frappe.set_route('Form', new_doc.doctype, new_doc.name);

				}
			});
		}	
	},
	before_workflow_action: function(frm){
		if(frm.doc.workflow_state == 'Pending Approval' && frm.doc.request_for_material_approver != frappe.session.user){
			frappe.throw(__("You are not authorized to approve!!"));
		}
	},
	setup: function(frm) {
		
		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.ordered_qty) ? "green" : "orange"; });

		frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			};
		});

		// set item reservation in child table
		frm.set_query('item_reservation', 'items', (frm, cdt, cdn) => {
			let row = locals[cdt][cdn];
		    return {
		        filters: {
		            item_code: ['=', row.item_code],
					rfm: ['=', row.parent]
		        }
		    }
		})
		//  end set item reservation
		if(frm.doc.docstatus==1 && frappe.session.user==frm.doc.request_for_material_approver && frm.doc.status!='Approved'){
			var df = frappe.meta.get_docfield("Request for Material Item","reject_item", cur_frm.doc.name);
            df.hidden = 0;
		}
		set_item_field_property(frm);
	},
	onload: function(frm) {
		
		erpnext.utils.add_item(frm);
		
		if(frm.is_new() && !frm.doc.requested_by){
			frm.set_value('requested_by', frappe.session.user);
		}

		set_t_warehouse_hidden(frm);
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
		if(frm.doc.workflow_state=="Approved"&& frm.doc.docstatus==1){
			set_intro(frm);
		}
		frm.events.make_custom_buttons(frm);
		add_stock_entry_buttons(frm);
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
		if(frm.doc.workflow_state == "Approved" || frm.doc.workflow_state == "Rejected"){
			frm.set_df_property('items', 'allow_on_submit', 0);
			frm.set_df_property('items', 'read_only', 1);
		}
		if(frm.is_new()){
			frappe.call({
				doc: frm.doc,
				method: 'get_default_warehouse',
				callback: function(r) {
					if(r && r.default_warehouse){
						frm.set_value('t_warehouse', r.default_warehouse);
					}
					else{
						frm.set_value('t_warehouse', '');
					}
				}
			});
		}
		set_filters(frm);
		set_warehouse_filters(frm);
		toggle_child_table_fields(frm);

		if(frm.doc.linked_request_for_material){
			frm.set_df_property('purpose', 'read_only', 1);
		}
		add_purchase_rfm_button(frm);
	},
	items_on_form_rendered: (frm) => {
	},
	before_items_remove: (frm) => {
	},
	items_add: (frm) => {
	},
	items_remove: (frm) => {
	},
	items_move: (frm) => {
	},
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved' && frappe.user.has_role("Stock User")) {
			
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
					if(item.custom_rfp_quantity < item.qty){
						purchase_item_exist = true;
						
					}
				});

				if(purchase_item_exist && frappe.user_roles.includes("Warehouse Supervisor") && frm.doc.purpose=="Purchase"){
					frm.add_custom_button(__("Request for Purchase"),
						function(){
							
							frm.events.make_request_for_purchase(frm)
						}, __('Create'))
							
							
						
						
				}

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
								var stock_entry_button_name = __("Material Transfer");
								if(frm.doc.type == "Individual"){
									stock_entry_button_name = __("Material Issue");
								}
								if(frappe.user_roles.includes("Warehouse Supervisor")){
									frm.add_custom_button(stock_entry_button_name, () => frm.events.make_stock_entry(frm), __('Create'));
								}
								}
								
						});
						
						if(any_items_ordered){
							frm.add_custom_button(__("Make Delivery Note"),
						 	    () => frm.events.make_delivery_note(frm), __('Create'));
						}

					}
				}
				else {	
					if(purchase_item_exist && frappe.user_roles.includes("Warehouse Supervisor" && frm.doc.purpose=="Purchase") ){
							frm.add_custom_button(__("Request for Purchase"),
								() => frm.events.make_request_for_purchase(frm), __('Create'));
					}
							
						
					if(any_items_ordered){
						frm.add_custom_button(__("Make Delivery Note"),
							() => frm.events.make_delivery_note(frm), __('Create'));
					}
				}
			}
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},
	erf: function(frm) {
		fetch_erf_items(frm);
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

					if(frm.doc.type == 'Stock' && frm.doc.docstatus == 0){
						if(item.description && !item.requested_description){
							frappe.model.set_value(item.doctype, item.name, 'requested_description', item.description);
						}
						if(item.item_name && !item.requested_item_name){
							frappe.model.set_value(item.doctype, item.name, 'requested_item_name', item.item_name);
						}
						frm.refresh_field('items');
					}
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
	validate_rfm_type : function(frm){
		
		// ensure that the purpose field is set throw an error if it is not
		if((!frm.doc.purpose)&& (frappe.user_roles.includes("Warehouse Supervisor"))){
			frappe.throw(__("Cannot Create Document. Purpose field needs to be selected"));
		}
	},
	make_request_for_purchase: async function(frm) {
				await frm.events.validate_rfm_type(frm);
				

                if (frm.is_dirty()) {
                        frappe.msgprint(__("Please save your changes before creating a Request for Purchase."));
                        return;
		}

                const items_to_purchase = frm.doc.items.filter(d => d.pur_qty > 0 && !d.rejected_item);
                if (items_to_purchase.length === 0) {
                        frappe.msgprint(__("There are no items marked for purchasing."));
                        return;
		}

                let dialog = new frappe.ui.Dialog({
                        title: __('Create Request for Purchase'),
                        fields: [
                                {
                                        fieldtype: 'HTML',
                                        options: __("Create a purchase request for all items, or select specific items?")
                                }
                        ],
                        primary_action_label: __('Select Items'),
                        primary_action: () => {
                                dialog.hide();
                                let selection_dialog = new frappe.ui.Dialog({
                                        title: __('Select Items and Quantities for RFP'),
                                        fields: [
                                                {
                                                        fieldname: 'items_html',
                                                        fieldtype: 'HTML'
                                                }
                                        ],
                                        primary_action_label: __('Create RFP'),
                                        primary_action: () => {
                                                let selected_items = [];
                                                selection_dialog.get_field('items_html').$wrapper.find('tbody tr').each(function() {
                                                        let row = $(this);
                                                        if (row.find('.select-item').prop('checked')) {
                                                                let qty_to_rfp = parseFloat(row.find('.qty-to-rfp').val() || 0);
                                                                let pending_qty = parseFloat(row.find('.pending-qty').text());
                                                                if (qty_to_rfp > pending_qty) {
                                                                        frappe.throw(__("Quantity for item {0} cannot exceed pending quantity.", [row.data('item-code')]));
                                                                }
                                                                if (qty_to_rfp > 0) {
                                                                        selected_items.push({
                                                                                'item_code': row.data('item-code'),
                                                                                'qty': qty_to_rfp,
                                                                                'request_for_material_item': row.data('item-name')
                                                                        });
                                                                }
                                                        }
                                                });

                                                if (selected_items.length === 0) {
                                                        frappe.msgprint(__('Please select at least one item with a quantity greater than 0.'));
                                                        return;
                                                }

                                                frappe.call({
                                                        method: "one_fm.purchase.doctype.request_for_material.request_for_material.create_partial_request_for_purchase",
                                                        args: {
                                                                source_name: frm.doc.name,
                                                                items: selected_items
                                                        },
                                                        callback: function(r) {
                                                                if (r.message) {
                                                                        selection_dialog.hide();
                                                                        frappe.set_route('Form', r.message.doctype, r.message.name);
                                                                }
                                                        },
                                                        freeze: true,
                                                        freeze_message: __('Creating Request for Purchase...')
                                                });
                                        }
                                });

                                let items_with_pending_qty = frm.doc.items.filter(d => (d.qty - (d.custom_rfp_quantity || 0)) > 0 && !d.rejected_item);

                                let table_html = `
                                <table class="table table-bordered" style="width: 100%;">
                                        <thead>
                                                <tr>
                                                        <th style="width: 5%;"><input type="checkbox" class="select-all-items"></th>
                                                        <th style="width: 55%;">${__('Item')}</th>
                                                        <th style="width: 20%;">${__('Pending Qty')}</th>
                                                        <th style="width: 20%;">${__('Qty for RFP')}</th>
                                                </tr>
                                        </thead>
                                        <tbody>
                                        </tbody>
                                </table>`;
                                selection_dialog.get_field('items_html').$wrapper.html(table_html);
                                let tbody = selection_dialog.get_field('items_html').$wrapper.find('tbody');

                                items_with_pending_qty.forEach(item => {
                                        let pending_qty = item.qty - (item.custom_rfp_quantity || 0);
                                        let row_html = `
                                                <tr data-item-name="${item.name}" data-item-code="${item.item_code}">
                                                        <td><input type="checkbox" class="select-item" checked></td>
                                                        <td>${item.item_code}: ${item.requested_item_name}</td>
                                                        <td class="pending-qty">${pending_qty}</td>
                                                        <td><input type="number" class="form-control qty-to-rfp" value="${pending_qty}" max="${pending_qty}" min="0"></td>
                                                </tr>
                                        `;
                                        tbody.append(row_html);
                                });

                                selection_dialog.get_field('items_html').$wrapper.find('.select-all-items').on('change', function() {
                                        selection_dialog.get_field('items_html').$wrapper.find('.select-item').prop('checked', $(this).prop('checked'));
                                });

                                selection_dialog.show();
                        },
                        secondary_action_label: __('All Items'),
                        secondary_action: () => {
                                dialog.hide();
                                frappe.model.open_mapped_doc({
                                        method: "one_fm.purchase.doctype.request_for_material.request_for_material.make_request_for_purchase",
                                        frm: frm
                                });
                        }
                });
                dialog.show();
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
		set_filters(frm);
		toggle_child_table_fields(frm);
	},
	project: function(frm) {
		set_t_warehouse_hidden(frm);
		set_warehouse_filters(frm);
	},
	department: function(frm) {
		set_warehouse_filters(frm);
	},
	site: function(frm) {
		set_warehouse_filters(frm);
	}
});



function add_stock_entry_buttons(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.workflow_state === 'Approved') {
        if (frm.doc.purpose === "Transfer") {
            frm.add_custom_button(__('Material Transfer'), function() {
                create_stock_entry(frm, 'Material Transfer');
            }, __('Create'));
            
            frm.add_custom_button(__('Material Transfer - In Transit'), function() {
                create_stock_entry(frm, 'Material Transfer-In Transit');
            }, __('Create'));
        }
        
        if (frm.doc.purpose === "Issue") {
            frm.add_custom_button(__('Material Issue'), function() {
                create_stock_entry(frm, 'Material Issue');
            }, __('Create'));

            check_and_show_employee_uniform_button(frm);
        }
    }
}

function check_and_show_employee_uniform_button(frm) {
    let has_uniform_items = frm.doc.items && frm.doc.items.some(
        item => item.is_uniform_request && item.employee
    );
    
    if (!has_uniform_items) {
        return;
    }
    
    frappe.call({
        method: 'one_fm.purchase.doctype.request_for_material.request_for_material.has_pending_uniform_items',
        args: {
            rfm_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message === true) {
                frm.add_custom_button(__('Employee Uniform'), function() {
                    create_employee_uniform_from_rfm(frm);
                }, __('Create'));
            }
        }
    });
}

function create_employee_uniform_from_rfm(frm) {
    let uniform_items = frm.doc.items.filter(
        item => item.is_uniform_request && item.employee && !item.linked_employee_uniform
    );
    
    if (uniform_items.length === 0) {
        frappe.msgprint({
            title: __('No Uniform Items'),
            message: __('All uniform items have already been processed or there are no uniform request items with assigned employees.'),
            indicator: 'orange'
        });
        return;
    }
    
    frappe.call({
        method: 'one_fm.purchase.doctype.request_for_material.request_for_material.create_employee_uniform',
        args: {
            rfm_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating Employee Uniform documents...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __(r.message.message),
                    indicator: 'green'
                }, 5);
                
                frm.reload_doc();
                
                if (r.message.created_uniforms && r.message.created_uniforms.length > 0) {
                    let uniform_html = '<table class="table table-bordered">';
                    uniform_html += '<thead><tr><th>Employee Uniform</th><th>Employee</th><th>Items</th><th>Total Qty</th></tr></thead>';
                    uniform_html += '<tbody>';
                    
                    r.message.created_uniforms.forEach(uniform => {
                        uniform_html += `<tr>
                            <td><a href="/app/employee-uniform/${uniform.name}" target="_blank">${uniform.name}</a></td>
                            <td>${uniform.employee_name} (${uniform.employee})</td>
                            <td>${uniform.total_items}</td>
                            <td>${uniform.total_quantity}</td>
                        </tr>`;
                    });
                    
                    uniform_html += '</tbody></table>';
                    
                    frappe.msgprint({
                        title: __('Employee Uniforms Created Successfully'),
                        message: uniform_html,
                        indicator: 'green',
                        primary_action: {
                            label: __('View First Uniform'),
                            action: function() {
                                frappe.set_route('Form', 'Employee Uniform', r.message.created_uniforms[0].name);
                            }
                        }
                    });
                }
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __('Error'),
                message: __('Failed to create Employee Uniform documents. Please check the error log.'),
                indicator: 'red'
            });
        }
    });
}

function create_stock_entry(frm, stock_entry_type) {
    frappe.call({
        method: 'one_fm.purchase.doctype.request_for_material.request_for_material.create_stock_entry_from_rfm',
        args: {
            rfm_name: frm.doc.name,
            stock_entry_type: stock_entry_type
        },
        callback: function(r) {
            if (r.message) {
                frappe.set_route('Form', 'Stock Entry', r.message);
            }
        }
    });
}

var set_t_warehouse_hidden = function(frm) {
	if(frm.doc.project){
		frm.set_df_property('t_warehouse', 'hidden', false);
	}
	else {
		frm.set_df_property('t_warehouse', 'hidden', true);
	}
}

frappe.ui.form.on('Request for Material Item', { // The child table is defined in a DoctType called "Dynamic Link"
	items_on_form_rendered: (frm) => {
	},
	before_items_remove: (frm) => {
	},
	items_add: (frm) => {
	},
	items_remove: (frm) => {
	},
	items_move: (frm) => {
	},
});

var set_filters = function(frm) {
	frm.set_query("erf", function() {
		return {
			filters: [
				['status', 'not in', ['Declined', 'Cancelled']]
			]
		};
	});
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
					if(designation.item_list && designation.item_list.length > 0){
						frm.get_field("items").grid.grid_rows[0].remove();
						for ( var i=0; i< designation.item_list.length; i++ ){
							let d = frm.add_child("items", {
								requested_item_name: designation.item_list[i].item_name,
								requested_description: "None",
								qty: designation.item_list[i].quantity,
								uom: designation.item_list[i].uom
							});
						}
						frm.refresh_field("items");
					}
				}
			},
			freeze: true,
			freeze_message: __('Fetching Data from Project to Set Default Data')
		});
	}
};
let validate_item_code = function(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) return;
    frm.doc.items.forEach((item, idx) => {
        if (!item.item_code) {
            frappe.throw(__("Item code must be filled for all items. Row {0} is missing item code.", [idx + 1]));
        }
    });
}


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
	var fields_dict = [];
	frappe.meta.get_docfield("Request for Material Item", "item_code", frm.doc.name).read_only = true;
	frappe.meta.get_docfield("Request for Material Item", "item_code", frm.doc.name).depends_on = 'eval:doc.docstatus==1';
	if((frm.doc.docstatus == 1 && (frappe.session.user == frm.doc.request_for_material_accepter || frm.doc.workflow_state == 'Approved')) || frm.doc.type == 'Stock'){
		frappe.meta.get_docfield("Request for Material Item", "item_code", frm.doc.name).read_only = false;
		frappe.meta.get_docfield("Request for Material Item", "item_code", frm.doc.name).depends_on = '';
	}
	if(frm.doc.type == 'Stock'){
		if(frm.is_new()){
			frm.clear_table('items');
			frm.refresh_field('items');
		}
		fields_dict = [{'fieldname': 'requested_item_name', 'read_only': true}, {'fieldname': 'requested_description', 'read_only': true}];
		frappe.meta.get_docfield("Request for Material Item", "requested_item_name", frm.doc.name).reqd = false;
		frappe.meta.get_docfield("Request for Material Item", "requested_description", frm.doc.name).reqd = false;
	}
	else if((frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved')){
		var fields = ['requested_item_name', 'requested_description', 'qty', 'uom', 'stock_uom'];
		fields.forEach((field, i) => {
			fields_dict[i] = {'fieldname': field, 'read_only': true}
		});
	}
	else{
		fields_dict = [{'fieldname': 'requested_item_name', 'read_only': false}, {'fieldname': 'requested_description', 'read_only': false}];
		frappe.meta.get_docfield("Request for Material Item", "requested_item_name", frm.doc.name).reqd = true;
		frappe.meta.get_docfield("Request for Material Item", "requested_description", frm.doc.name).reqd = true;
	}
	if (fields_dict.length > 0){
		set_item_field_read_only(frm, fields_dict);
	}
};

var set_item_field_read_only = function(frm, fields) {
	fields.forEach((field, i) => {
		frappe.meta.get_docfield("Request for Material Item", field.fieldname, frm.doc.name).read_only = field.read_only;
	});
};

var set_warehouse_filters = function(frm) {
	var wh_filters = {'is_group': 0};
	if(frm.doc.type == 'Department'){
		wh_filters = {'is_group': 0, 'department': frm.doc.department};
	}
	if(frm.doc.type == 'Project'){
		wh_filters = {'is_group': 0, 'one_fm_project': frm.doc.project};
		if(frm.doc.site){
			wh_filters['one_fm_site'] = frm.doc.site;
		}
	}
	frm.set_query("t_warehouse", function() {
		return {
			filters: wh_filters
		};
	});
}

var set_employee_from_the_session_user = function(frm) {
	if(frappe.session.user != 'Administrator'){
		frappe.db.get_value('Employee', {'user_id': frappe.session.user} , 'name', function(r) {
			if(r && r.name){
				frm.set_value('employee', r.name);
			}
			else{
				frappe.msgprint(__('Employee or Employee email not created for the user <b>{0}</b>', [frappe.session.user]))
			}
		});
	}
};

var set_employee_or_project = function(frm) {
	if(frm.doc.type){
		frm.set_df_property('department', 'read_only', false);
		frm.set_df_property('employee', 'reqd', false);
		frm.set_df_property('department', 'reqd', false);
		frm.set_df_property('project', 'reqd', false);
		frm.set_df_property('customer', 'reqd', (frm.doc.type=='Project')?true:false);
		frm.set_df_property('site', 'reqd', (frm.doc.type=='Project')?true:false);
		if(frm.doc.type=='Individual'){
			frm.set_df_property('employee', 'reqd', true);
			// Check if employee exit for the session user to set employee field
			set_employee_from_the_session_user(frm);
		}
		else if(frm.doc.type=='Department'){
			frm.set_df_property('department', 'reqd', true);
			// Check if employee exit for the session user to set employee field
			set_employee_from_the_session_user(frm);
		}
		else if(frm.doc.type=='Project'|| frm.doc.type=='Project Mobilization'){
			frm.set_df_property('project', 'reqd', true);
		}
		else if(frm.doc.type=='Onboarding'){
			frm.set_df_property('erf', 'reqd', true);
			frm.set_df_property('department', 'read_only', true);
		}
	}
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
	setup: (frm)=>{
	},
	qty: function (frm, doctype, name) {
	},
	pur_qty: function (frm, doctype, name){
		var d = locals[doctype][name];
		if (d.quantity_to_transfer > (d.qty+d.pur_qty) || d.quantity_to_transfer > (d.qty+d.pur_qty)){
			d.quantity_to_transfer = d.qty-d.pur_qty
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
	},
	item_code: function(frm, doctype, name) {
		const item = locals[doctype][name];
		// set childtable button color
		if(!item.item_reservation){
			frm.fields_dict["items"].grid.frm.$wrapper.find('.btn.btn-xs.btn-default').addClass('btn-primary');
		}
		item.rate = 0;
		set_schedule_date(frm);
		if(!item.item_code){
			frappe.model.set_value(item.doctype, item.name, 'item_name', '');
		}
		frm.events.get_item_data(frm, item);
	},
	create_reservation: (frm, cdt, cdn)=>{
		let row = locals[cdt][cdn];
		if(row.item_code && !row.item_reservation){
			frappe.db.get_value('Item Reservation', {
				rfm: frm.doc.name,
				item_code:row.item_code
			}, [
				'item_code', 'from_date', 'to_date',
				'name', 'qty']
			).then(r=>{
				if(Object.keys(r.message).length){
					row.item_reservation = r.message.name;
					row.from_date = r.message.from_date;
					row.to_date = r.message.to_date;
					row.reserve_qty = r.message.qty;
					frm.refresh_field('items');
				}else{
					let d = new frappe.ui.Dialog({
					    title: `Create Reservation for <b>${row.item_code}</b>`,
					    fields: [
					        {
					            label: 'Item',
					            fieldname: 'item_code',
					            fieldtype: 'Link',
								options: 'Item',
								reqd:1,
								read_only:1,
								default: row.item_code
					        },
					        {
					            label: 'Quantity',
					            fieldname: 'qty',
					            fieldtype: 'Float'
					        },
					        {
					            label: 'From Date',
					            fieldname: 'from_date',
					            fieldtype: 'Date',
								reqd:1
					        },
					        {
					            label: 'To Date',
					            fieldname: 'to_date',
					            fieldtype: 'Date',
								reqd:1
					        },
							{
					            label: 'Comment',
					            fieldname: 'comment',
					            fieldtype: 'Small Text',
					        }
					    ],
					    primary_action_label: 'Submit',
					    primary_action(values) {
							if(values.qty>row.qty){
								frappe.throw(__('Reservation quantity cannot be greater that requested quantity'));
							} else if(values.qty<=0){
								frappe.throw(__('Value cannnot be 0'));
							} else if(values.from_date > values.to_date){
					            frappe.throw(__(
					                {
					                    title:__('Invalid'),
					                    message:__('Reserve From date cannot be after Reserver To date.')
					                }
					            ))
					        } else {
								values.rfm = row.parent;
								frm.call('create_reservation', {filters:values}).then(r => {
									if(r.message){
										row.item_reservation = r.message.name;
										row.from_date = r.message.from_date;
										row.to_date = r.message.to_date;
										row.reserve_qty = r.message.qty;
										frm.refresh_field('items');
									}
							  })
							}
					        d.hide();
					    }
					});
					d.show();
				}

			})

		}

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
	},
	show_stock_level: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.item_code){
			var dialog = new frappe.ui.Dialog({
				title: 'Stock Level',
				width: 100,
				fields: [
					{fieldtype: "HTML", fieldname: "stock_level_html"},
				]
			});
			var stock_level_html = "";
			frappe.call({
				method: 'erpnext.stock.dashboard.item_dashboard.get_data',
				args: {
					item_code: row.item_code
				},
				callback: function (r) {
					if(r.message && r.message.length > 0){
						var data = r.message;
						var $wrapper = dialog.fields_dict.stock_level_html.$wrapper;
						var template = `
							<div class="row">
								<div class="col-sm-3" style="margin-top: 1px;">
									<b>Warehouse</b>
								</div>
								<div class="col-sm-3" style="margin-top: 1px;">
									<b>Item</b>
								</div>
								<div class="col-sm-4" style="margin-top: 1px; text-align: center;">
									<b>Stock Level</b>
								</div>
							</div>
							<hr/>
							{% for d in data %}
								<div class="dashboard-list-item">
									<div class="row">
										<div class="col-sm-3" style="margin-top: 8px;">
											<a data-type="warehouse" data-name="{{ d.warehouse }}">{{ d.warehouse }}</a>
										</div>
										<div class="col-sm-3" style="margin-top: 8px;">
											{% if show_item %}
												<a data-type="item"
													data-name="{{ d.item_code }}">{{ d.item_code }}
													{% if d.item_name != d.item_code %}({{ d.item_name }}){% endif %}
												</a>
											{% endif %}
										</div>
										<div class="col-sm-4">
											<span class="inline-graph">
												<span class="inline-graph-half" title="{{ __("Reserved Qty") }}">
													<span class="inline-graph-count">{{ d.total_reserved }}</span>
													<span class="inline-graph-bar">
														<span class="inline-graph-bar-inner"
															style="width: {{ cint(Math.abs(d.total_reserved)/max_count * 100) || 5 }}%">
														</span>
													</span>
												</span>
												<span class="inline-graph-half" title="{{ __("Actual Qty {0} / Waiting Qty {1}", [d.actual_qty, d.pending_qty]) }}">
													<span class="inline-graph-count">
														{{ d.actual_qty }} {{ (d.pending_qty > 0) ? ("(" + d.pending_qty+ ")") : "" }}
													</span>
													<span class="inline-graph-bar">
														<span class="inline-graph-bar-inner dark"
															style="width: {{ cint(d.actual_qty/max_count * 100) }}%">
														</span>
														{% if d.pending_qty > 0 %}
														<span class="inline-graph-bar-inner" title="{{ __("Projected Qty") }}"
															style="width: {{ cint(d.pending_qty/max_count * 100) }}%">
														</span>
														{% endif %}
													</span>
												</span>
											</span>
										</div>
									</div>
								</div>
							{% endfor %}
						`;

						var max_count = 0;
						data.forEach(function (d) {
							d.actual_or_pending = d.projected_qty + d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
							d.pending_qty = 0;
							d.total_reserved = d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
							if (d.actual_or_pending > d.actual_qty) {
								d.pending_qty = d.actual_or_pending - d.actual_qty;
							}

							max_count = Math.max(d.actual_or_pending, d.actual_qty,
								d.total_reserved, max_count);
						});
						stock_level_html = frappe.render_template(template, {'data': data, 'show_item': true, 'max_count': max_count})
						$wrapper
						.html(stock_level_html);
					}
					else{
						var msg = __("No Stock Available..!")
						dialog.fields_dict.stock_level_html.html(msg.bold())
					}
				},
				freeze: true
			});
			dialog.show();
		}
	}
});


erpnext.buying.MaterialRequestController = class MaterialRequestController extends erpnext.buying.BuyingController {
	tc_name() {
		this.get_terms();
	}

	item_code() {
		// to override item code trigger from transaction.js
	}

	validate_company_and_party() {
		return true;
	}

	calculate_taxes_and_totals() {
		return;
	}

	validate() {
		set_schedule_date(this.frm);
	}

	items_add(doc, cdt, cdn) {
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
	}

	items_on_form_rendered() {
		set_schedule_date(this.frm);
	}

	schedule_date() {
		set_schedule_date(this.frm);
	}
};


// for backward compatibility: combine new and previous states
extend_cscript(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
	}
};

function set_intro(frm){
	if(!frm.doc.purpose){
		frm.set_intro("Please select the Purpose of this Request for Material before converting.");
	}
	 let intro_string = "Only Warehouse Supervisor can convert this Request for Material to Request for Purchase/Purchase RFM or Material Transfer/Material Issue."
	 frm.set_intro(intro_string);
}

function set_t_warehouse(frm){
	if(frm.doc.t_warehouse){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "t_warehouse");
	}
};


function toggle_child_table_fields(frm) {
	
    if (frm.doc.type === "Stock") {
		
        frm.fields_dict['items'].grid.toggle_display('is_service_request', false);
		frm.fields_dict['items'].grid.toggle_display('attach_photo', false);
		frm.fields_dict['items'].grid.toggle_display('item_url', false);
	}
}

function add_purchase_rfm_button(frm){
	if(!(frm.doc.docstatus == 1 && frm.doc.workflow_state == 'Approved' && frappe.user_roles.includes('Warehouse Supervisor'))){
		return;
	}

	if(!frm.doc.linked_request_for_material && (["Transfer", "Issue"].includes(frm.doc.purpose))){
		frm.add_custom_button(__('Purchase RFM'), () => frm.events.purchase_rfm(frm), __('Create'));
		frm.page.set_inner_btn_group_as_primary(__('Create'));
	}

}
