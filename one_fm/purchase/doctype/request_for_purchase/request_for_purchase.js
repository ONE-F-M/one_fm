// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request for Purchase', {
	refresh: function(frm) {
		set_intro_related_to_status(frm);
		frm.events.make_custom_buttons(frm);
		update_currency_labels(frm);
		toggle_base_currency_columns(frm);
		update_total_labels(frm);
        // Toggle currency field editability based on RFP status
        toggle_currency_readonly(frm);

		

		if (frm.doc.workflow_state === "Approved" && frm.doc.docstatus === 1) {
			if (frm.fields_dict["items"] && frm.fields_dict["items"].grid) {
				frm.fields_dict["items"].grid.update_docfield_property("qty", "read_only", 1);
			}
			if (frm.fields_dict["items_to_order"] && frm.fields_dict["items_to_order"].grid) {
				frm.fields_dict["items_to_order"].grid.update_docfield_property("qty", "read_only", 1);
			}

		}

		if (frm.doc.status && frm.doc.docstatus === 1) {
				const status_colors = {
					"Draft": "grey",
					"Draft Request": "grey",
					"Accepted": "blue",
					"Approved": "blue",
					"To Order": "orange",
					"Partially Ordered": "yellow",
					"Ordered": "green",
					"Rejected": "red",
					"Submitted": "blue",
					"Cancelled": "red"
				};
				
				const color = status_colors[frm.doc.status] || "grey";
				
				frm.page.clear_indicator();
				
				frm.page.set_indicator(frm.doc.status, color);
			}

	},
    status: function(frm) {
        // Ensure UI reflects currency edit rules when status changes
        toggle_currency_readonly(frm);
    },
	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus == 1 && frappe.user.has_role('Purchase Officer')){
			if(frm.doc.workflow_state === 'Approved') {
				// Only show Update Items if at least one item has purchased_quantity < qty
				const can_update = (frm.doc.items || []).some(item => {
					return (typeof item.purchased_quantity === 'number' && typeof item.qty === 'number' && item.purchased_quantity < item.qty);
				});
				if (can_update) {
					frm.add_custom_button(__("Update Items"), () => {
						frappe.dom.freeze(__('Fetching latest pending quantities...'));
						if (!frm.doc.request_for_material) {
							frappe.dom.unfreeze();
							frappe.msgprint(__('No Request for Material linked.'));
							return;
						}
						frappe.db.get_doc('Request for Material', frm.doc.request_for_material)
							.then(rfm_doc => {
								let rfm_items = (rfm_doc.items || []);
								let pending_qty_map = {};
								(frm.doc.items || []).forEach(item => {
									let rfm_item = rfm_items.find(i => i.name === item.custom_request_for_material_item);
									
									pending_qty_map[item.item_code] = rfm_item 
										? rfm_item.custom_pending_quantity
										: item.pending_qty;
								});
								frappe.dom.unfreeze();
								
								let dialog = new frappe.ui.Dialog({
									title: __("Update Items"),
									fields: [
										{ fieldname: 'items_html', fieldtype: 'HTML' }
									],
									primary_action_label: __("Done"),
									primary_action: () => {
										let updated_items = [];
										let invalid_rows = [];
										dialog.get_field('items_html').$wrapper.find('tbody tr').each(function() {
											let row = $(this);
											let name = row.data('name');
											
											
											let rfp_qty_cell = parseFloat(row.find('.rfp-qty-cell').text()) || 0;
											let item_code = row.data('item-code');
											let item_name = row.find('.item-name-cell').text();
											let qty = parseFloat(row.find('.qty-input').val());
											let orig = (frm.doc.items_to_order || []).find(i => i.name === name || i.item_code === item_code);
											let ordered_qty = orig && typeof orig.ordered_qty === 'number' ? orig.ordered_qty : 0;
											let pending_qty = pending_qty_map[item_code];
											
											
											if (qty < ordered_qty) {
												invalid_rows.push(`${item_code || item_name}: New quantity (${qty}) cannot be less than ordered quantity (${ordered_qty})`);
											}
											if (qty > (pending_qty+rfp_qty_cell)) {
												invalid_rows.push(`${item_code || item_name}: New quantity (${qty}) cannot be greater than ordered quantity, pending quantity and quantity in this RFP (${pending_qty + rfp_qty_cell})`);
											}
											updated_items.push({
												name,
												item_code,
												item_name,
												qty
											});
										});
										if (invalid_rows.length > 0) {
											frappe.msgprint({
												message: __('The following rows are invalid:<br><ul>' + invalid_rows.map(r => `<li>${r}</li>`).join('') + '</ul>'),
												indicator: 'red',
												title: __('Invalid Quantities')
											});
											return;
										}
										frappe.prompt(
											[{
												fieldtype: 'Data',
												label: __('Reason for Update'),
												fieldname: 'reason',
												reqd: 1
											}],
											(data) => {
												frappe.call({
													doc: frm.doc,
													method: "update_rfp_items",
													args: {
														updated_items: JSON.stringify(updated_items),
														reason: data.reason
													},
													callback: function(r) {
														if (!r.exc) {
															frm.reload_doc();
															frappe.msgprint(__("Items updated successfully."));
														}
													},
													freeze: true,
													freeze_message: __("Updating Items...")
												});
											}, __("Reason for Update")
										);
										dialog.hide();
									},
								});
								let table_html = `
								<table class="table table-bordered">
									<thead>
										<tr>
											<th>${__('Item Code')}</th>
											<th>${__('Item Name')}</th>
											<th>${__('Quantity')}</th>
											<th>${__('Ordered Quantity')}</th>
											<th>${__('Pending Quantity (RFM)')}</th>
											<th>${__('RFP Quantity')}</th>
											<th></th>
										</tr>
									</thead>
									<tbody>
									</tbody>
								</table>`;
								dialog.get_field('items_html').$wrapper.html(table_html);
								let tbody = dialog.get_field('items_html').$wrapper.find('tbody');
								(frm.doc.items_to_order || []).forEach(item => {
									let ordered_qty = typeof item.ordered_qty === 'number' ? item.ordered_qty : 0;
									let pending_qty = pending_qty_map[item.item_code];
									let rfp_qty = typeof item.qty === 'number' ? item.qty : '';
									let remove_disabled = ordered_qty > 0 ? 'disabled' : '';
									let row_html = `
										<tr data-name="${item.name}" data-item-code="${item.item_code}">
											<td>${item.item_code}</td>
											<td class="item-name-cell">${item.item_name}</td>
											<td><input type="number" class="form-control qty-input" value="${item.qty}"></td>
											<td class="ordered-qty-cell">${ordered_qty}</td>
											<td class="pending-qty-cell">${pending_qty}</td>
											<td class="rfp-qty-cell">${rfp_qty}</td>
											<td><button class="btn btn-danger btn-xs remove-item" ${remove_disabled}>${__("Remove")}</button></td>
										</tr>
									`;
									tbody.append(row_html);
								});
								dialog.get_field('items_html').$wrapper.on('click', '.remove-item', function() {
									$(this).closest('tr').remove();
								});
								dialog.show();
							});
					});
				}
			}

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
    get_requested_items_to_order: async function(frm) {
        frm.clear_table('items_to_order');
        
        if (!frm.doc.items || frm.doc.items.length === 0) {
            return;
        }
        
        let rfm_item_names = frm.doc.items
            .map(item => item.custom_request_for_material_item)
            .filter(name => name);
        
        if (rfm_item_names.length === 0) {
            frm.doc.items.forEach((item) => {
                var items_to_order = frm.add_child('items_to_order');
                items_to_order.item_code = item.item_code;
                items_to_order.item_name = item.item_name;
                items_to_order.uom = item.uom;
                items_to_order.t_warehouse = item.t_warehouse;
                items_to_order.qty_requested = item.qty;
                items_to_order.qty = item.qty;
                items_to_order.delivery_date = item.schedule_date;
                items_to_order.request_for_material = item.request_for_material;
                items_to_order.request_for_material_item = item.custom_request_for_material_item;
                items_to_order.is_refundable = item.is_refundable || 0;
                items_to_order.margin_known = item.margin_known || '';
                items_to_order.margin_type = item.margin_type || '';
                items_to_order.margin_rate_or_amount = item.margin_rate_or_amount || 0;
            });
            frm.refresh_fields();
            return;
        }
        
        let rfm_items_data = await frappe.call({
            method: 'one_fm.purchase.doctype.request_for_purchase.request_for_purchase.get_rfm_item_uom_data',
            args: {
                rfm_item_names: rfm_item_names
            }
        });
        
        let rfm_items_map = {};
        if (rfm_items_data.message) {
            rfm_items_data.message.forEach(rfm_item => {
                rfm_items_map[rfm_item.name] = rfm_item;
            });
        }

        let item_codes = frm.doc.items.map(item => item.item_code).filter(code => code);
        
        let last_purchase_details = await frappe.call({
            method: 'one_fm.purchase.doctype.request_for_purchase.request_for_purchase.get_last_purchase_details',
            args: {
                item_codes: item_codes
            }
        });
        
        let last_purchase_map = last_purchase_details.message || {};
        
        frm.doc.items.forEach((item) => {
            var items_to_order = frm.add_child('items_to_order');
            items_to_order.item_code = item.item_code;
            items_to_order.item_name = item.item_name;
            items_to_order.t_warehouse = item.t_warehouse;
            items_to_order.qty_requested = item.qty;
            items_to_order.qty = item.qty;
            items_to_order.delivery_date = item.schedule_date;
            items_to_order.request_for_material = item.request_for_material;
            items_to_order.request_for_material_item = item.custom_request_for_material_item;
            
            let rfm_item = rfm_items_map[item.custom_request_for_material_item];
            if (rfm_item) {
                items_to_order.uom = rfm_item.uom;
                items_to_order.stock_uom = rfm_item.stock_uom;
                items_to_order.conversion_factor = rfm_item.conversion_factor || 1;
                
                let conversion_factor = rfm_item.conversion_factor || 1;
                items_to_order.stock_qty = flt(item.qty || 0) * flt(conversion_factor);
                
                // Map margin fields from RFM item
                items_to_order.is_refundable = rfm_item.is_refundable || 0;
                items_to_order.margin_known = rfm_item.margin_known || '';
                items_to_order.margin_type = rfm_item.margin_type || '';
                items_to_order.margin_rate_or_amount = rfm_item.margin_rate_or_amount || 0;
            } else {
                items_to_order.uom = item.uom;
                items_to_order.conversion_factor = 1;
                items_to_order.stock_qty = item.qty;
                
                // Fallback to item's own margin fields if RFM item not found
                items_to_order.is_refundable = item.is_refundable || 0;
                items_to_order.margin_known = item.margin_known || '';
                items_to_order.margin_type = item.margin_type || '';
                items_to_order.margin_rate_or_amount = item.margin_rate_or_amount || 0;
            }

            if (last_purchase_map[item.item_code]) {
                items_to_order.last_purchase_supplier = last_purchase_map[item.item_code].supplier;
                items_to_order.last_purchase_rate = last_purchase_map[item.item_code].rate;
            }
        });
        
        frm.refresh_fields();
    },
	supplier: function(frm) {
		set_supplier_to_items_to_order(frm);
	},
	currency: function(frm) {
		if (!frm.doc.currency) return;
		if (!frm.fields_dict.exchange_rate) return;

		// Use hidden field company_currency instead of API call
		let from_currency = frm.doc.company_currency;
		if (!from_currency) {
			frappe.show_alert({message: __('Company currency (company_currency) not found; set exchange rate manually.'), indicator: 'orange'});
			frm.set_df_property('exchange_rate', 'read_only', 0);
			return;
		}
		update_currency_labels(frm);
		toggle_base_currency_columns(frm);
		update_total_labels(frm);

		let to_currency = frm.doc.currency;
		// If same currency set 1 and make read only
		if (from_currency === to_currency) {
			frm.set_value('exchange_rate', 1.0);
			frm.set_df_property('exchange_rate', 'read_only', 1);
			frappe.show_alert({message: __('Exchange Rate set to 1.0 (same currency).'), indicator: 'green'});
			return;
		}

		let cache_key = `currency_exchange_${from_currency}_${to_currency}`;
		// Optionally keep last successful rate in cache (Q6) but still refetch (Q7)
		let previous_cached_rate = window[cache_key];
		// Preserve existing value before fetch in case not found (Q3)
		let previous_value = frm.doc.exchange_rate;

		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Currency Exchange',
				fields: ['name','exchange_rate','date'],
				filters: {
					from_currency: to_currency,
					to_currency: from_currency,
					date: ['<=', frappe.datetime.get_today()]
				},
				order_by: 'date desc',
				limit_page_length: 1
			},
			callback: function(res) {
				let records = res && res.message ? res.message : [];
				if (records.length) {
					let rate = flt(records[0].exchange_rate);
					// Update value & make read only (Q3)
					frm.set_value('exchange_rate', rate);
					frm.set_df_property('exchange_rate', 'read_only', 1);
					frm.refresh_field('exchange_rate');
					window[cache_key] = rate;
					frappe.show_alert({message: __('Exchange Rate fetched: {0}', [rate]), indicator: 'green'});
				} else {
					// No record: leave previous value, editable (Q3)
					frm.set_value('exchange_rate', previous_value);
					frm.set_df_property('exchange_rate', 'read_only', 1);
					frappe.show_alert({message: __('No Currency Exchange found for {0} -> {1}. Set rate manually.', [from_currency, to_currency]), indicator: 'orange'});
					if (previous_cached_rate) {
						frappe.show_alert({message: __('Using previously cached rate: {0}', [previous_cached_rate]), indicator: 'yellow'});
					}
				}
			},
			error: function() {
				// On error restore previous and allow editing
				frm.set_value('exchange_rate', previous_value);
				frm.set_df_property('exchange_rate', 'read_only', 0);
				frappe.show_alert({message: __('Error fetching exchange rate. Set manually.'), indicator: 'red'});
				if (previous_cached_rate) {
					frappe.show_alert({message: __('Cached rate available: {0}', [previous_cached_rate]), indicator: 'yellow'});
				}
			}
		});


	},
	onload: function(frm) {
        update_currency_labels(frm);
		toggle_base_currency_columns(frm);
		update_total_labels(frm);
        // Apply currency readonly rules on load as well
        toggle_currency_readonly(frm);
    },
	exchange_rate: function(frm) {
        recalculate_all_items(frm);
    },
	validate: function(frm) {
        validate_uom_conversion_factors(frm);
    },
	before_submit: function(frm) {
        validate_uom_conversion_factors(frm);
    }
});


function validate_uom_conversion_factors(frm) {
    let has_error = false;
    let error_rows = [];
    
    frm.doc.items_to_order.forEach(function(item) {
        if (item.uom && item.stock_uom && item.uom !== item.stock_uom) {
            if (!item.conversion_factor || item.conversion_factor <= 0) {
                has_error = true;
                error_rows.push(item.idx);
            }
        }
    });
    
    if (has_error) {
        frappe.throw(__('Row(s) {0}: UOM Conversion Factor is mandatory when UOM differs from Stock UOM', [error_rows.join(', ')]));
    }
}


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

function update_currency_labels(frm) {
    let currency = frm.doc.currency || frm.doc.company_currency || 'KWD';
    
    frm.fields_dict['items_to_order'].grid.update_docfield_property(
        'rate',
        'label',
        __('Rate ({0})', [currency])
    );
    
    frm.fields_dict['items_to_order'].grid.update_docfield_property(
        'amount',
        'label',
        __('Amount ({0})', [currency])
    );
    
    frm.refresh_field('items_to_order');
}

function update_total_labels(frm) {
    let company_currency = frm.doc.company_currency || 'KWD';
    
    frm.set_df_property('base_total', 'label', __('Total ({0})', [company_currency]));
}


function toggle_base_currency_columns(frm) {
    let show_base_currency = frm.doc.currency && frm.doc.currency !== frm.doc.company_currency;
    let company_currency = frm.doc.company_currency || 'KWD';
    

    frm.fields_dict['items_to_order'].grid.update_docfield_property(
        'base_rate',
        'label',
        __('Rate ({0})', [company_currency])
    );
    
    frm.fields_dict['items_to_order'].grid.update_docfield_property(
        'base_amount',
        'label',
        __('Amount ({0})', [company_currency])
    );

    frm.fields_dict['items_to_order'].grid.update_docfield_property(
        'base_rate',
        'in_list_view',
        show_base_currency ? 1 : 0
    );
    
    frm.fields_dict['items_to_order'].grid.update_docfield_property(
        'base_amount',
        'in_list_view',
        show_base_currency ? 1 : 0
    );
	
    if (show_base_currency) {
        frm.fields_dict['items_to_order'].grid.update_docfield_property('item_name', 'columns', 1);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('item_code', 'columns', 1);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('qty', 'columns', 1);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('rate', 'columns', 1);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('amount', 'columns', 1);
    } else {
        frm.fields_dict['items_to_order'].grid.update_docfield_property('item_name', 'columns', 2);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('item_code', 'columns', 2);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('qty', 'columns', 2);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('rate', 'columns', 2);
        frm.fields_dict['items_to_order'].grid.update_docfield_property('amount', 'columns', 2);
    }
    frm.fields_dict['items_to_order'].grid.reset_grid();
    frm.refresh_field('items_to_order');
}

function toggle_currency_readonly(frm) {
    // Acceptance Criteria:
    // - If status is 'To Order' => Currency remains editable
    // - If status is 'Partially Ordered' => Currency cannot be changed
    // Default: editable unless explicitly blocked
    try {
        const status = frm.doc.status;
        if (status === 'Partially Ordered' || status === 'Ordered') {
            frm.set_df_property('currency', 'read_only', 1);
            frm.set_df_property('currency', 'description', __('Currency cannot be changed once the RFP is Ordered or Partially Ordered.'));
            frm.set_df_property('exchange_rate', 'read_only', 1);
        } else {
            frm.set_df_property('currency', 'read_only', 0);
            frm.set_df_property('currency', 'description', null);
            frm.set_df_property('exchange_rate', 'read_only', 0);
        }
        frm.refresh_field('currency');
        frm.refresh_field('exchange_rate');
    } catch (e) {
        // Non-blocking UI safeguard
        console && console.warn && console.warn('toggle_currency_readonly error', e);
    }
}

function recalculate_all_items(frm) {
    if (!frm.doc.exchange_rate) return;
    
    frm.doc.items_to_order.forEach(function(item) {
        calculate_item_values(frm, item.doctype, item.name);
    });
    
    frm.refresh_field('items_to_order');
    calculate_totals(frm);
}



frappe.ui.form.on('Request for Purchase Quotation Item', {
    rate: function(frm, cdt, cdn) {
        calculate_stock_rate(frm, cdt, cdn);
        calculate_item_values(frm, cdt, cdn);
    },
    
    qty: function(frm, cdt, cdn) {
        update_stock_qty(frm, cdt, cdn);
        calculate_item_values(frm, cdt, cdn);
    },
    
    item_code: function(frm, cdt, cdn) {
        set_item_defaults(frm, cdt, cdn);
    },
    
    uom: function(frm, cdt, cdn) {
        handle_uom_change(frm, cdt, cdn);
        check_conversion_factor_required(frm, cdt, cdn);
    },
    
    stock_uom: function(frm, cdt, cdn) {
        handle_uom_change(frm, cdt, cdn);
        check_conversion_factor_required(frm, cdt, cdn);
    },
    
    conversion_factor: function(frm, cdt, cdn) {
        validate_and_update_conversion_factor(frm, cdt, cdn);
		calculate_stock_rate(frm, cdt, cdn);
    },
    
    items_to_order_remove: function(frm) {
        calculate_totals(frm);
    }
});

function set_item_defaults(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (!row.item_code) {
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Item',
            filters: { name: row.item_code },
            fieldname: ['stock_uom']
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, 'stock_uom', r.message.stock_uom);
                
                if (!row.uom) {
                    frappe.model.set_value(cdt, cdn, 'uom', r.message.stock_uom);
                    frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
                    update_stock_qty(frm, cdt, cdn);
                    calculate_stock_rate(frm, cdt, cdn);
                } else {
                    fetch_conversion_factor(frm, cdt, cdn);
                }
            }
        }
    });
}

function handle_uom_change(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (!row.uom || !row.stock_uom) {
        return;
    }
    
    if (row.uom === row.stock_uom) {
        frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
        update_stock_qty(frm, cdt, cdn);
        calculate_stock_rate(frm, cdt, cdn);
    } else {
        fetch_conversion_factor(frm, cdt, cdn);
    }
}

function validate_and_update_conversion_factor(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (!row.conversion_factor || row.conversion_factor <= 0) {
        frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
        frappe.msgprint({
            title: __('Invalid Conversion Factor'),
            message: __('Conversion factor must be greater than 0. Setting to 1.'),
            indicator: 'red'
        });
        return;
    }
    
    update_stock_qty(frm, cdt, cdn);
    calculate_stock_rate(frm, cdt, cdn);
    show_conversion_hint(frm, cdt, cdn);
}

function fetch_conversion_factor(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (!row.item_code || !row.uom || !row.stock_uom) {
        return;
    }
    
    if (row.uom === row.stock_uom) {
        frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
        update_stock_qty(frm, cdt, cdn);
        calculate_stock_rate(frm, cdt, cdn);
        return;
    }
    
    fetch_from_item_master(frm, cdt, cdn);
}

function fetch_from_item_master(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Item',
            name: row.item_code
        },
        callback: function(r) {
            if (r.message) {
                let item = r.message;
                let conversion_found = false;
                
                if (item.uoms && item.uoms.length > 0) {
                    for (let uom_row of item.uoms) {
                        if (uom_row.uom === row.uom) {
                            frappe.model.set_value(cdt, cdn, 'conversion_factor', uom_row.conversion_factor || 1);
                            update_stock_qty(frm, cdt, cdn);
                            calculate_stock_rate(frm, cdt, cdn);
                            conversion_found = true;
                            break;
                        }
                    }
                }
                
                if (!conversion_found) {
                    fetch_from_uom_conversion(frm, cdt, cdn, row.stock_uom, row.uom);
                }
            } else {
                fetch_from_uom_conversion(frm, cdt, cdn, row.stock_uom, row.uom);
            }
        }
    });
}

function fetch_from_uom_conversion(frm, cdt, cdn, from_uom, to_uom) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'UOM Conversion Factor',
            filters: {
                from_uom: to_uom,
                to_uom: from_uom
            },
            fields: ['value'],
            limit: 1
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                frappe.model.set_value(cdt, cdn, 'conversion_factor', r.message[0].value || 1);
                update_stock_qty(frm, cdt, cdn);
                calculate_stock_rate(frm, cdt, cdn);
            } else {
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'UOM Conversion Factor',
                        filters: {
                            from_uom: from_uom,
                            to_uom: to_uom
                        },
                        fields: ['value'],
                        limit: 1
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            let inverse_factor = 1 / (r.message[0].value || 1);
                            frappe.model.set_value(cdt, cdn, 'conversion_factor', inverse_factor);
                            update_stock_qty(frm, cdt, cdn);
                            calculate_stock_rate(frm, cdt, cdn);
                        } else {
                            frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
                            update_stock_qty(frm, cdt, cdn);
                            calculate_stock_rate(frm, cdt, cdn);
                            frappe.msgprint({
                                title: __('Conversion Factor Not Found'),
                                message: __('No conversion factor found between {0} and {1}.<br><br><b>Please enter manually:</b><br>• Example 1: If 1 {0} = 5 {1}, enter 5<br>• Example 2: If 1 {0} = 0.2 {1}, enter 0.2<br><br>Formula: Stock Qty = Qty × Conversion Factor', [to_uom, from_uom]),
                                indicator: 'orange'
                            });
                        }
                    }
                });
            }
        }
    });
}

function update_stock_qty(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let conversion_factor = flt(row.conversion_factor) || 1;
    let qty = flt(row.qty) || 0;
    let stock_qty = qty * conversion_factor;
    
    if (row.stock_uom) {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'UOM',
                filters: { name: row.stock_uom },
                fieldname: ['must_be_whole_number']
            },
            callback: function(r) {
                if (r.message && r.message.must_be_whole_number) {
                    if (stock_qty % 1 !== 0) {
                        frappe.model.set_value(cdt, cdn, 'stock_qty', 0);
                        frappe.msgprint({
                            title: __('Fractional Value Not Allowed'),
                            message: __('{0} cannot have a fractional value.', [row.stock_uom]),
                            indicator: 'red'
                        });
                        frappe.utils.play_sound('error');
                        return;
                    }
                }
                frappe.model.set_value(cdt, cdn, 'stock_qty', stock_qty);
            }
        });
    } else {
        frappe.model.set_value(cdt, cdn, 'stock_qty', stock_qty);
    }
}

function calculate_stock_rate(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let conversion_factor = flt(row.conversion_factor) || 1;
    let rate = flt(row.rate) || 0;
    let stock_rate = 0;
    
    if (row.uom && row.stock_uom && row.uom !== row.stock_uom) {
        if (conversion_factor > 0) {
            stock_rate = rate / conversion_factor;
        }
    } else {
        stock_rate = rate;
    }
    
    frappe.model.set_value(cdt, cdn, 'stock_rate', stock_rate);
}

function show_conversion_hint(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (!row.uom || !row.stock_uom || row.uom === row.stock_uom) {
        return;
    }
    
    let conversion_factor = flt(row.conversion_factor) || 1;
    let qty = flt(row.qty) || 0;
    let stock_qty = qty * conversion_factor;
    let rate = flt(row.rate) || 0;
    let stock_rate = conversion_factor > 0 ? rate / conversion_factor : 0;
    let amount = qty * rate;
    
    let hint_message = __('Conversion Details:<br>• 1 {0} = {1} {2}<br>• Stock Qty: {3} {0} × {1} = <b>{4} {2}</b><br>• Stock Rate: {5} ÷ {1} = <b>{6} per {2}</b><br>• Amount: {3} {0} × {5} = <b>{7}</b>', 
        [
            row.uom, 
            conversion_factor.toFixed(6), 
            row.stock_uom, 
            qty, 
            stock_qty.toFixed(6), 
            rate.toFixed(2), 
            stock_rate.toFixed(6),
            amount.toFixed(2)
        ]);
    
    frappe.show_alert({
        message: hint_message,
        indicator: 'green'
    }, 7);
}

function calculate_item_values(frm, cdt, cdn) {
    let item = locals[cdt][cdn];
    let exchange_rate = flt(frm.doc.exchange_rate) || 1;
    
    if (item.rate && item.qty) {
        let amount = flt(item.rate) * flt(item.qty);
        let base_rate = flt(item.rate) * exchange_rate;
        let base_amount = flt(item.qty) * base_rate;

        frappe.model.set_value(cdt, cdn, 'amount', flt(amount, 2));
        frappe.model.set_value(cdt, cdn, 'base_rate', flt(base_rate, 2));
        frappe.model.set_value(cdt, cdn, 'base_amount', flt(base_amount, 2));
    }
    
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total = 0;
    let base_total = 0;
    
    frm.doc.items_to_order.forEach(function(item) {
        total += flt(item.amount);
        base_total += flt(item.base_amount);
    });
    
    frm.set_value('total', flt(total, 2));
    frm.set_value('base_total', flt(base_total, 2));
}

function check_conversion_factor_required(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (row.uom && row.stock_uom && row.uom !== row.stock_uom) {
        if (!row.conversion_factor || row.conversion_factor <= 0) {
            frappe.msgprint({
                title: __('Conversion Factor Required'),
                message: __('Row #{0}: Please provide a UOM Conversion Factor as the UOM ({1}) differs from Stock UOM ({2})', [row.idx, row.uom, row.stock_uom]),
                indicator: 'orange'
            });
        }
    }
}