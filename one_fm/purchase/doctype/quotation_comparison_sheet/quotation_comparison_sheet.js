// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quotation Comparison Sheet', {
	refresh: function(frm) {
		set_filter_for_quotation_in_item(frm);
		set_filter_for_quotation_item_in_item(frm);
		set_custom_buttons(frm);
	},
	request_for_quotation: function(frm) {
		set_quotation_against_rfq(frm);
		set_custom_buttons(frm)
		frm.clear_table('items');
	},
	request_for_purchase: function(frm){
		set_rfq(frm);
	},
	compare_quotation_by: function(frm) {
		set_quotation_against_rfq(frm);
	}
});

var set_rfq = function(frm) {
	if(!frm.doc.request_for_quotation && frm.doc.request_for_purchase){
		frappe.db.get_value('Request for Supplier Quotation', {'request_for_purchase': frm.doc.request_for_purchase}, 'name', function(r) {
			if(r){
				frm.set_value('request_for_quotation', r.name);
			}
		});
	}
};

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
					var quotations = r.message;
					quotations.forEach((quotation, i) => {
						var qtn = frm.add_child('quotations');
						qtn.quotation = quotation.name
						qtn.supplier = quotation.supplier
						qtn.estimated_delivery_date = quotation.estimated_delivery_date
						qtn.grand_total = quotation.grand_total
						qtn.item_details = get_quotation_item_details(frm, quotation);
						qtn.attach_sq = quotation.attach_sq
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
	qtn_item.description = item.description
	qtn_item.estimated_delivery_date = quotation.estimated_delivery_date
	qtn_item.quantity = item.qty
	qtn_item.uom = item.uom
	qtn_item.rate = item.rate
	qtn_item.amount = item.amount
};



// SET BUTTONS FOR QUOTATION COMPARISON
let set_custom_buttons = (frm)=>{
	if(![2,1].includes(frm.doc.docstatus)){
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
			customer_filter(frm);
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

// complete filters table
let complete_filters_table = (frm, data, selected_by)=>{
	frm.clear_table('items');
	let suppliers_dict = {};
	frm.doc.quotations.forEach((item, i) => {
		suppliers_dict[item.quotation] = {supplier:item.supplier, name:item.supplier_name}
	});

	// get RFSQ
	frappe.db.get_doc(
		'Request for Supplier Quotation',
		frm.doc.request_for_quotation
	).then(res=>{
		let items_obj = {}
		res.items.forEach((item, i) => {
			items_obj[item.item_name] = item.schedule_date;
		});
		// process table
		let grand_total = 0;
		data.forEach((item, i) => {
			frm.add_child('items', {
				quotation_item: item.quotation_item,
				quotation: item.quotation,
				item_name: item.item_name,
				description: item.description,
				qty: item.quantity,
				uom: item.uom,
				rate: item.rate,
				amount: item.amount,
				schedule_date: items_obj[item.item_name],
				estimated_delivery_date: item.estimated_delivery_date,
				supplier: suppliers_dict[item.quotation].supplier,
				supplier_name: suppliers_dict[item.quotation].name
			})
			grand_total = grand_total + item.amount;
		});
		frm.refresh_field('items');
		frm.set_value('selected_by', selected_by);
		frm.set_value('grand_total', grand_total);
		frappe.show_alert(`Quotation selected by <b>${selected_by}</b>`, 5);

	})

}


// custom filter
let customer_filter = (frm)=>{
	let items = get_quotation_items(frm);
	const table_fields = [
			{
				fieldname: "item_name", fieldtype: "Select",
				in_list_view: 1, label: "Quotation Item",
				options: items, reqd: 1,
				change: function (x) {
					console.log(dialog.fields_dict.items_detail.df.data)
					dialog.fields_dict.items_detail.df.data.some(d => {
						if (d.item_name==this.doc.item_name && d.idx != this.doc.idx) {
							console.log(this.doc)
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
				// {
				// 	fieldtype: '', label: __('Company'), default: frappe.defaults.get_default('company'),
				// 	options: 'Company', fieldname: 'company', reqd: 1
				// },
				// {
				// 	fieldtype: 'Link', label: __('POS Profile'),
				// 	options: 'POS Profile', fieldname: 'pos_profile', reqd: 1,
				// 	get_query: () => pos_profile_query,
				// 	onchange: () => fetch_pos_payment_methods()
				// },
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
				console.log(values);
				values.items_detail.forEach((item, i) => {
					if(!item.select_by){
						frappe.throw(`Please select option for
							<b>${item.item_name}</b> on row <b>${item.idx}</>`)
					}
				});
				// process
				process_custom_filter(values);


				dialog.hide();
			},
			primary_action_label: __('Submit')
		});
		dialog.show();
		// console.log(dialog)
		// initialize dialog table
		items.forEach((item, i) => {
			dialog.fields_dict.items_detail.df.data.push(
				{ item_name: item}
			);
		});
		dialog.fields_dict.items_detail.grid.refresh();


		// process filter
		let process_custom_filter = (values)=>{
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
