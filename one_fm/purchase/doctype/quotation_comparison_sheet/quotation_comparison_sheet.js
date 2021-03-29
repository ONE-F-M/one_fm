// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quotation Comparison Sheet', {
	refresh: function(frm) {
		set_filter_for_quotation_in_item(frm);
		set_filter_for_quotation_item_in_item(frm);
	},
	request_for_quotation: function(frm) {
		set_quotation_against_rfq(frm);
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
