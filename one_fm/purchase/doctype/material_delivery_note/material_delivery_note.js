// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Material Delivery Note', {
	purchase_receipt: function(frm) {
		// set_items(frm);
	}
});

var set_items = function(frm) {
	frm.clear_table('items');
	if(frm.doc.purchase_receipt){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Purchase Receipt',
				filters: {'name': frm.doc.purchase_receipt}
			},
			callback: function(r) {
				if(r && r.message){
					var rfp = r.message;
					if(rfp.items){
						console.log("DDD");
						rfp.items.forEach((item, i) => {
							var d_item = frm.add_child('items');
							console.log(item);
							d_item.item_code = item.item_code
							d_item.item_name = item.item_name
							d_item.description = item.description
							d_item.item_group = item.item_group
							d_item.qty = item.qty
							d_item.uom = item.uom
							d_item.batch_no = item.batch_no
						});
					}
				}
				frm.refresh_field('items');
			}
		});
	}
};
