// Copyright (c) 2020, ONE FM and Contributors
// For license information, please see license.txt

// store request_for_quotation and related data in here
window.rfq_dataset = {
	items_filter_arr: {}
}


let make_rfq_dataset_itemsfilter = (frm, item_name, order_by)=>{
	// filter and sort items
	if(order_by==='Best Rate'){
		window.rfq_dataset.items_filter_arr[item_name] = frm.doc.quotation_items.filter((a, b) => {
			return a.item_name===item_name
		}).sort((x, y)=> {
			return x.rate - y.rate
		})
	} else {
		window.rfq_dataset.items_filter_arr[item_name] = frm.doc.quotation_items.filter((a, b) => {
			return a.item_name===item_name
		}).sort((x, y)=> {
			return new Date(x.estimated_delivery_date) - new Date(y.estimated_delivery_date)
		})
	}
}



frappe.ui.form.on('Quotation Comparison Sheet', {
	validate: function (frm) {
		frm.trigger('get_rfq');
	},
	refresh: function(frm) {
		frm.trigger('set_query');
		set_filter_for_quotation_in_item(frm);
		set_filter_for_quotation_item_in_item(frm);
		set_custom_buttons(frm);
		frm.trigger('get_rfq');

		// Add "Create Purchase Order" button for submitted QCS
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Create Purchase Order"), function() {
				create_purchase_order(frm);
			});
			frm.change_custom_button_type(__("Create Purchase Order"), null, "primary");
		}

		// Add "Sync Quotations" button for draft QCS
		if (frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.request_for_quotation) {
			frm.add_custom_button(__("Sync New Quotations"), function() {
				frm.call("sync_quotations").then(res => {
					frm.reload_doc();
				});
			});
		}
	},
	request_for_quotation: function(frm) {
		set_quotation_against_rfq(frm);
		set_custom_buttons(frm)
		frm.clear_table('items');
	},
	set_query: (frm)=>{
		// filter submitted rfq
		frm.set_query('request_for_quotation', () => {
		    return {
		        filters: {
		            docstatus: 1
		        }
		    }
		})
	},
	get_rfq: (frm)=>{
		if(frm.doc.request_for_quotation && frm.doc.request_for_material){
			frm.call('get_rfq', {
					rfq:frm.doc.request_for_quotation,
					rfm:frm.doc.request_for_material,
					}).then(
				res=>{
					window.rfq_dataset.quotation_items = {};
					window.rfq_dataset.items_qtyobj = {};
					window.rfq_dataset.suppliers_dict = {};
					window.rfq_dataset.items_codes = {};
					window.rfq_dataset.rfq = res.message.rfq;
					window.rfq_dataset.rfn = res.message.rfm;
					res.message.rfq.items.forEach((item, i) => {
						window.rfq_dataset.items_qtyobj[item.item_name] = item.qty;
						window.rfq_dataset.quotation_items[item.item_name] = item
					});
					res.message.rfm.items.forEach((item, i) => {
						window.rfq_dataset.items_codes[item.requested_item_name || item.item_name] = item.item_code;
					});
					frm.doc.quotations.forEach((item, i) => {
						window.rfq_dataset.suppliers_dict[item.quotation] = {supplier:item.supplier, name:item.supplier_name}
					});
				}
			)
		}
	}
});


frappe.ui.form.on('Comparison Sheet Quotation', {
	quotations_add: function(frm) {
		set_filter_for_quotation_in_item(frm);
		set_filter_for_quotation_item_in_item(frm);
	},
	quotations_remove: function(frm) {
		set_filter_for_quotation_in_item(frm);
		set_filter_for_quotation_item_in_item(frm);
	}
});

var set_filter_for_quotation_in_item = function(frm) {
	var qtn_name_list = [];
	if(frm.doc.quotations){
		frm.doc.quotations.forEach((item, i) => {
			qtn_name_list.push(item.quotation);
		});
	}
	frm.set_query('quotation', 'items', function() {
		return{
			filters: {
				'name': ['in', qtn_name_list]
			}
		}
	});
};

var set_filter_for_quotation_item_in_item = function(frm) {
	var qtn_name_list = [];
	if(frm.doc.quotation_items){
		frm.doc.quotation_items.forEach((item, i) => {
			qtn_name_list.push(item.quotation_item);
		});
	}
	frm.set_query('quotation_item', 'items', function() {
		return{
			filters: {
				'name': ['in', qtn_name_list]
			}
		}
	});
};

var set_quotation_against_rfq = function(frm) {
	if(frm.doc.request_for_quotation){
		frm.clear_table('quotations');
		frm.clear_table('quotation_items');
		frappe.call({
			method: 'one_fm.purchase.doctype.quotation_comparison_sheet.quotation_comparison_sheet.get_quotation_against_rfq',
			args: {'rfq': frm.doc.request_for_quotation},
			callback: function(r) {
				if(r && r.message){
					window.rfq_dataset.rfsq = r.message;
					var quotations = r.message;
					quotations.forEach((quotation, i) => {
						var qtn = frm.add_child('quotations');
						qtn.quotation = quotation.name
						qtn.supplier = quotation.supplier
						qtn.estimated_delivery_date = quotation.valid_till
						qtn.grand_total = quotation.grand_total
						qtn.item_details = get_quotation_item_details(frm, quotation);
					});
					frm.refresh_field('quotations');
					frm.refresh_field('quotation_items');
					set_filter_for_quotation_in_item(frm);
					set_filter_for_quotation_item_in_item(frm);
				}
			}
		});
		frm.refresh_field('quotations');
		frm.refresh_field('quotation_items');
	}
};


var get_quotation_item_details = function(frm, quotation) {
	var quotation_item_details_html = `<table border="1px grey"  bordercolor="silver" style="width: 100%; height="100"">
	<th><b>Item Name</b></th>
	<th><b>Quantity</b></th>
	<th style="text-align: right;"><b>Rate</b></th>
	<th style="text-align: right;"><b>Amount</b></th>
	<th style="text-align: center;"><b>UOM</b></th>
	<th><b>Description</b></th>`;

  quotation.items.forEach(function(val, i){
		var i = i+1
		quotation_item_details_html += `<tr>`
		quotation_item_details_html += `<td style="width: 8%">` + (val.item_name ? val.item_name : '') + "</td>";
		quotation_item_details_html += `<td style="width: 8%; text-align: right;">` + (val.qty ? val.qty : '') + "</td>";
		quotation_item_details_html += `<td style="width: 8%; text-align: right;">` + (val.rate ? val.rate : '') + "</td>";
		quotation_item_details_html += `<td style="width: 8%; text-align: right;">` + (val.amount ? val.amount : '') + "</td>";
		quotation_item_details_html += `<td style="width: 8%">` + (val.uom ? val.uom : '') + "</td>";
		quotation_item_details_html += `<td style="width: 14% word-wrap: break-all" contenteditable = 'false'>` + (val.description? val.description : '') + "</td>";
		quotation_item_details_html += `</tr>`;
		set_quotation_item_details(frm, val, quotation);
	});
	quotation_item_details_html +=	`</table>`;
	return quotation_item_details_html;
};

var set_quotation_item_details = function(frm, item, quotation) {
	var qtn_item = frm.add_child('quotation_items');
	qtn_item.quotation = item.parent
	qtn_item.quotation_item = item.name
	qtn_item.item_name = item.item_name
	qtn_item.item_code = item.item_code
	qtn_item.description = item.description
	qtn_item.estimated_delivery_date = quotation.valid_till
	qtn_item.quantity = item.qty
	qtn_item.uom = item.uom
	qtn_item.rate = item.rate
	qtn_item.amount = item.amount
	qtn_item.supplier = quotation.supplier
	qtn_item.supplier_name = quotation.supplier_name
};



// SET BUTTONS FOR QUOTATION COMPARISON
let set_custom_buttons = (frm)=>{
	if(!frm.is_new() && ![2,1].includes(frm.doc.docstatus)){
		// Custom buttons in groups
		frm.add_custom_button('Best Rate from One Supplier', () => {
			best_price_same_supplier(frm);
		}, 'Analyse');

		// best_price_many_suppliers
		frm.add_custom_button('Best Rate from Many Supplier', () => {
			best_price_many_supplier(frm);
		}, 'Analyse');

		// best_price_many_suppliers
		frm.add_custom_button('Earliest Delivery', () => {
			earliest_delivery(frm);
		}, 'Analyse');

		// best_price_many_suppliers
		frm.add_custom_button('Custom', () => {
			custom_filter(frm);
		}, 'Analyse');
	}
}

let get_quotation_items = (frm) => {
	let items = [];
	frm.doc.quotation_items.forEach((item, i) => {
		if (!items.includes(item.item_name)){
			items.push(item.item_name)
		}
	});
	return items
}

//  filter for best price by same supplier
let best_price_same_supplier = (frm)=>{
	// set global item filter
	get_quotation_items(frm).forEach((item, i) => {
		make_rfq_dataset_itemsfilter(frm, item, 'Best Rate');
	});

	// select best price
	let ordered_quotations = frm.doc.quotations.sort((a, b) => {
	    return a.grand_total - b.grand_total;
	})[0];
	// filter all items for selected quotation
	let best_quotation_items = frm.doc.quotation_items.filter(
		item => item.quotation === ordered_quotations.quotation
	);
	// append to selected filtered table
	complete_filters_table(frm, best_quotation_items, 'Best Rate from One Supplier');
}


//  filter for best price by many supplier
let best_price_many_supplier = (frm)=>{
	get_quotation_items(frm).forEach((item, i) => {
		make_rfq_dataset_itemsfilter(frm, item, 'Best Rate');
	});
	// select best items price
	let items = get_quotation_items(frm);

	let best_quotation_items = []
	items.forEach((item, i) => {
		best_quotation_items.push(
			frm.doc.quotation_items.filter((a, b) => {
			    return a.item_name===item
			}).sort((x, y)=> {
			    return x.rate - y.rate
			})[0]
		)
	});

	// // append to selected filtered table
	complete_filters_table(frm, best_quotation_items, 'Best Rate from Many Supplier');
}


//  filter based on earliest delivery
let earliest_delivery = (frm)=>{
	get_quotation_items(frm).forEach((item, i) => {
		make_rfq_dataset_itemsfilter(frm, item, 'Earliest Delivery');
	});
	// select earliest delivery
	let ordered_quotations = frm.doc.quotations.sort((a, b) => {
	    return new Date(a.estimated_delivery_date) - new Date(b.estimated_delivery_date);
	})[0];
	// filter all items for selected quotation
	let best_quotation_items = frm.doc.quotation_items.filter(
		item => item.quotation === ordered_quotations.quotation
	);
	// append to selected filtered table
	complete_filters_table(frm, best_quotation_items, 'Earliest Delivery');
}


// custom filter
let custom_filter = (frm)=>{
	let items = get_quotation_items(frm);
	const table_fields = [
			{
				fieldname: "item_name", fieldtype: "Select",
				in_list_view: 1, label: "Quotation Item",
				options: items, reqd: 1,
				change: function (x) {
					dialog.fields_dict.items_detail.df.data.some(d => {
						if (d.item_name==this.doc.item_name && d.idx != this.doc.idx) {

							this.doc.item_name = null;
							dialog.fields_dict.items_detail.grid.refresh();
							return frappe.utils.play_sound("error");
							frappe.throw('You cannot repeat same item')
							// d.opening_amount = this.value;
							return true;
						}
					});
				}
			},
			{
				fieldname: "select_by", fieldtype: "Select",
				in_list_view: 1, label: "Select by", reqd:1,
				options: ['Best Rate', 'Earliest Delivery Date'],
				default: null
			}
		];

	const dialog = new frappe.ui.Dialog({
			title: __('Custom Quotation Selection'),
			static: false,
			fields: [
				{
					fieldname: "items_detail",
					fieldtype: "Table",
					label: "Items",
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					reqd: 1,
					data: [],
					fields: table_fields
				}
			],
			primary_action: async function(values) {
				// validate values
				values.items_detail.forEach((item, i) => {
					if(!item.select_by){
						frappe.throw(`Please select option for
								<b>${item.item_name}</b> on row <b>${item.idx}</b>`)
					}
				});
				// process
				process_custom_filter(values);


				dialog.hide();
			},
			primary_action_label: __('Submit')
		});
		dialog.show();
		// initialize dialog table
		items.forEach((item, i) => {
			dialog.fields_dict.items_detail.df.data.push(
				{ item_name: item}
			);
		});
		dialog.fields_dict.items_detail.grid.refresh();


		// process filter
		let process_custom_filter = (values)=>{
			// set items sorting and filtering
			values.items_detail.forEach((item, i) => {
				make_rfq_dataset_itemsfilter(frm, item.item_name, item.select_by);
			});

			let filtered_items = []
			values.items_detail.forEach((item, i) => {
				if(item.select_by=='Best Rate'){
					filtered_items.push(
						frm.doc.quotation_items.filter(
							x => x.item_name === item.item_name
						).sort((a, b) => {
						    return a.rate - b.rate;
						})[0]
					)
				} else {
					filtered_items.push(
						frm.doc.quotation_items.filter(
							x => x.item_name === item.item_name
						).sort((a, b) => {
						    return new Date(a.estimated_delivery_date) - new Date(b.estimated_delivery_date);
						})[0]
					)
				}

			});
			complete_filters_table(frm, filtered_items, 'Custom');

		}
}


const reassign_remaining_items = (frm) => {

}

// complete filters table
let complete_filters_table = (frm, data, selected_by)=>{
	frm.clear_table('items');
	// process table

	let new_items = [];
	frm.trigger('get_rfq');
	let all_items = Object.keys(window.rfq_dataset.quotation_items);
	let data_items = [];
	let items_qty = {};

	// set missing items
	data.forEach((item, i) => {
		data_items.push(item.item_name);
		// delete from supplier_quotation;
		items_qty[item.item_name] = window.rfq_dataset.items_qtyobj[item.item_name];
		items_qty[item.item_name] = items_qty[item.item_name] - item.quantity;
		window.rfq_dataset.items_filter_arr[item.item_name] = window.rfq_dataset.items_filter_arr[item.item_name].filter(
			x => x.idx !== item.idx
		)
	})
	all_items.forEach((item, i) => {

		if(data_items.includes(item)){
			// pass
		} else {

			try {
				let missing_item = window.rfq_dataset.items_filter_arr[item][0];
				if(missing_item){
    				data.push(missing_item);
    				items_qty[item] = window.rfq_dataset.items_qtyobj[item]
    				items_qty[item] = items_qty[item] - missing_item.quantity;
					window.rfq_dataset.items_filter_arr[missing_item.item_name] = window.rfq_dataset.items_filter_arr[missing_item.item_name].filter(
    				x => x.idx !== missing_item.idx
    				)
    			}
			}
			catch(err) {
			  // pass
			}

		}
	});

	// end set missing items
	data.forEach((item, i) => {
		if(item.quantity>window.rfq_dataset.items_qtyobj[item.item_name]){
			item.quantity = window.rfq_dataset.items_qtyobj[item.item_name];
		}
		new_items.push(item);
		while (true) {
			if(items_qty[item.item_name]>0 && window.rfq_dataset.items_filter_arr[item.item_name]){
				if(window.rfq_dataset.items_filter_arr[item.item_name] && window.rfq_dataset.items_filter_arr[item.item_name][0]){
					let newitem = window.rfq_dataset.items_filter_arr[item.item_name][0];
					if(items_qty[item.item_name]>newitem.quantity){
						new_items.push(newitem);
						items_qty[item.item_name] = items_qty[item.item_name] - newitem.quantity;
						window.rfq_dataset.items_filter_arr[item.item_name] = window.rfq_dataset.items_filter_arr[item.item_name].filter(
							x => x.idx !== newitem.idx
						)
					} else {
						newitem.quantity = items_qty[item.item_name];
						new_items.push(newitem);
						items_qty[item.item_name] = items_qty[item.item_name] - newitem.quantity;
						window.rfq_dataset.items_filter_arr[item.item_name] = window.rfq_dataset.items_filter_arr[item.item_name].filter(
							x => x.idx !== newitem.idx
						)
						break;
					}

				} else {
					break;
				}
			} else {
				break;
			}
		}

	});

	// check quantity


	let grand_total = 0;
	new_items.forEach((item, i) => {
		frm.add_child('items', {
			quotation_item: item.quotation_item,
			quotation: item.quotation,
			item_name: item.item_name,
			description: item.description,
			qty: item.quantity,
			uom: item.uom,
			rate: item.rate,
			amount: item.amount,
			schedule_date: window.rfq_dataset.quotation_items[item.item_name].schedule_date,
			estimated_delivery_date: item.estimated_delivery_date,
			supplier: window.rfq_dataset.suppliers_dict[item.quotation].supplier,
			supplier_name: window.rfq_dataset.suppliers_dict[item.quotation].name,
			item_code: item.item_code || window.rfq_dataset.items_codes[item.item_name]
		})
		grand_total = grand_total + (item.quantity * item.rate);
	});
	frm.refresh_field('items');
	frm.set_value('selected_by', selected_by);
	frm.set_value('grand_total', grand_total);
	frappe.show_alert(`Quotation selected by <b>${selected_by}</b>`, 5);
}


// Dynamic grand_total recalculation when items are manually changed
frappe.ui.form.on('Quotation Comparison Sheet Item', {
	items_add: function(frm) {
		recalculate_grand_total(frm);
	},
	items_remove: function(frm) {
		recalculate_grand_total(frm);
	},
	qty: function(frm) {
		recalculate_grand_total(frm);
	},
	rate: function(frm) {
		recalculate_grand_total(frm);
	}
});

function recalculate_grand_total(frm) {
	let grand_total = 0;
	(frm.doc.items || []).forEach(function(item) {
		grand_total += (item.qty || 0) * (item.rate || 0);
	});
	frm.set_value("grand_total", grand_total);
}


const create_purchase_order = (frm)=>{
	frappe.confirm(__("Are you sure you want to create <b>Purchase Order(s)</b> from this Quotation Comparison Sheet?"),
    () => {
		frappe.call({
			method: "create_purchase_order",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Creating Purchase Orders..."),
			callback: function(r) {
				if (r.message && r.message.length) {
					frappe.set_route("List", "Purchase Order", {
						"custom_quotation_comparison_sheet": frm.doc.name,
						"status": "Draft"
					});
				}
			}
		});
    }, () => {
        // action to perform if No is selected
    })
}
