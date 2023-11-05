// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

{% include 'erpnext/public/js/controllers/buying.js' %};

erpnext.buying.QuotationFromSupplier = class QuotationFromSupplier extends erpnext.buying.BuyingController {
	setup() {
		super.setup();
	}
	request_for_quotation() {
		set_items(this.frm);
	}
	setup_queries(doc, cdt, cdn) {
		var me = this;

		me.frm.set_query('contact_person', erpnext.queries.contact_query);
		me.frm.set_query('supplier_address', erpnext.queries.address_query);

		me.frm.set_query('billing_address', erpnext.queries.company_address_query);
		me.frm.set_query("supplier", function() {
			return {
				query: "one_fm.purchase.utils.get_supplier_list",
				filters: {'request_for_quotation': me.frm.doc.request_for_quotation}
			}
		});
	}
}

var set_items = function(frm) {
	frm.clear_table('items');
	if(frm.doc.request_for_quotation){
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Request for Supplier Quotation',
				filters: {name: frm.doc.request_for_quotation}
			},
			callback: function(r) {
				if(r && r.message){
					var rfq = r.message;
					frm.doc.request_for_material = rfq.request_for_material;
					if(rfq.items){
						rfq.items.forEach((r_item, i) => {
							var item = frm.add_child('items');
							item.item_name = r_item.item_name
							item.description = r_item.description
							item.qty = r_item.qty
							item.uom = r_item.uom
							item.item_code = r_item.item_code
							item.warehouse = r_item.t_warehouse
						});
					}
				}
				frm.refresh_field('items');
			}
		});
	}
};

// for backward compatibility: combine new and previous states
extend_cscript(cur_frm.cscript, new erpnext.buying.QuotationFromSupplier({frm: cur_frm}));
