frappe.pages['stock-balance-1'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Purchase Dashboard'),
		single_column: true
	});
	page.start = 0;

	page.rfm_field = page.add_field({
		fieldname: 'rfm',
		label: __('RFM'),
		fieldtype:'Link',
		options:'Request for Material',
		change: function() {
			page.item_dashboard.start = 0;
			page.item_dashboard.refresh();
		}
	});
	//
	// page.item_field = page.add_field({
	// 	fieldname: 'item_code',
	// 	label: __('Item'),
	// 	fieldtype:'Link',
	// 	options:'Item',
	// 	change: function() {
	// 		page.item_dashboard.start = 0;
	// 		page.item_dashboard.refresh();
	// 	}
	// });
	//
	// page.item_group_field = page.add_field({
	// 	fieldname: 'item_group',
	// 	label: __('Item Group'),
	// 	fieldtype:'Link',
	// 	options:'Item Group',
	// 	change: function() {
	// 		page.item_dashboard.start = 0;
	// 		page.item_dashboard.refresh();
	// 	}
	// });

	// page.sort_selector = new frappe.ui.SortSelector({
	// 	parent: page.wrapper.find('.page-form'),
	// 	args: {
	// 		sort_by: 'projected_qty',
	// 		sort_order: 'asc',
	// 		options: [
	// 			{fieldname: 'projected_qty', label: __('Projected qty')},
	// 			{fieldname: 'reserved_qty', label: __('Reserved for sale')},
	// 			{fieldname: 'reserved_qty_for_production', label: __('Reserved for manufacturing')},
	// 			{fieldname: 'reserved_qty_for_sub_contract', label: __('Reserved for sub contracting')},
	// 			{fieldname: 'actual_qty', label: __('Actual qty in stock')},
	// 		]
	// 	},
	// 	change: function(sort_by, sort_order) {
	// 		page.item_dashboard.sort_by = sort_by;
	// 		page.item_dashboard.sort_order = sort_order;
	// 		page.item_dashboard.start = 0;
	// 		page.item_dashboard.refresh();
	// 	}
	// });

	// page.sort_selector.wrapper.css({'margin-right': '15px', 'margin-top': '4px'});

	frappe.require('assets/js/item-dashboard-1.min.js', function() {
		page.item_dashboard = new one_fm.purchase.ItemDashboard({
			parent: page.main,
		})

		page.item_dashboard.before_refresh = function() {
			this.rfm = page.rfm_field.get_value();
		}

		page.item_dashboard.refresh();

		var setup_click = function(doctype, doc_abbr) {
			page.main.on('click', 'a[data-type="'+ doc_abbr +'"]', function() {
				var name = $(this).attr('data-name');
				frappe.set_route('Form', doctype, name);
			});
		}

		setup_click('Request for Material', 'rfm');
		setup_click('Request for Purchase', 'rfp');
		setup_click('Quotation Comparison Sheet', 'qcs');
		setup_click('Purchase Order', 'po');
		setup_click('Purchase Receipt', 'pr');
		setup_click('Purchase Invoice', 'pi');

		page.main.on('click', 'div[data-type=pri]', function() {
			var name = $(this).attr('data-name');
			frappe.call({
				method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
				args: {source_name: name},
				callback: function (r) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			});
		});
	});
}
