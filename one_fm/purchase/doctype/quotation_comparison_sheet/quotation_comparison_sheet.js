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
	// Custom buttons in groups
	frm.add_custom_button('Best Price/One Supplier', () => {
	    best_price_same_supplier(frm);
	}, 'Analyse');

	// best_price_many_suppliers
	frm.add_custom_button('Best Price/Many Supplier', () => {
	    best_price_many_supplier(frm);
	}, 'Analyse');

	// best_price_many_suppliers
	frm.add_custom_button('Earliest Delivery', () => {
	    earliest_delivery(frm);
	}, 'Analyse');
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
	complete_filters_table(frm, best_quotation_items, 'Best Price/One Supplier');
}


//  filter for best price by many supplier
let best_price_many_supplier = (frm)=>{
	// select best items price
	let items = []
	frm.doc.quotation_items.forEach((item, i) => {
		if (!items.includes(item.item_name)){
			items.push(item.item_name)
		}
	});

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
	complete_filters_table(frm, best_quotation_items, 'Best Price/Many Supplier');
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
