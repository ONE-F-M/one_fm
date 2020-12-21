frappe.pages['stock-balance-1'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Purchase Dashboard'),
		single_column: true
	});
	page.start = 0;

	// page.warehouse_field = page.add_field({
	// 	fieldname: 'warehouse',
	// 	label: __('Warehouse'),
	// 	fieldtype:'Link',
	// 	options:'Warehouse',
	// 	change: function() {
	// 		page.item_dashboard.start = 0;
	// 		page.item_dashboard.refresh();
	// 	}
	// });
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

		page.item_dashboard.refresh();

		var setup_click = function(doctype, doc_abbr) {
			page.main.on('click', 'a[data-type="'+ doc_abbr +'"]', function() {
				var name = $(this).attr('data-name');
				frappe.set_route('Form', doctype, name)
			});
		}

		setup_click('Request for Material', 'rfm');
		setup_click('Request for Purchase', 'rfp');
		setup_click('Purchase Order', 'po');
		setup_click('Purchase Receipt', 'pr');
	});
}
