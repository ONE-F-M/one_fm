frappe.provide('one_fm.purchase');

one_fm.purchase.ItemDashboard = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		this.make();
	},
	make: function() {
		var me = this;
		this.start = 0;
		if(!this.sort_by) {
			// this.sort_by = 'projected_qty';
			this.sort_order = 'asc';
		}

		this.content = $(frappe.render_template('item_dashboard_1')).appendTo(this.parent);
		this.result = this.content.find('.result');

		this.content.on('click', '.btn-move', function() {
			handle_move_add($(this), "Move")
		});

		this.content.on('click', '.btn-add', function() {
			handle_move_add($(this), "Add")
		});

		function handle_move_add(element, action) {
			let item = unescape(element.attr('data-item'));
			let warehouse = unescape(element.attr('data-warehouse'));
			let actual_qty = unescape(element.attr('data-actual_qty'));
			let disable_quick_entry = Number(unescape(element.attr('data-disable_quick_entry')));
			let entry_type = action === "Move" ? "Material Transfer": null;

			if (disable_quick_entry) {
				open_stock_entry(item, warehouse, entry_type);
			} else {
				if (action === "Add") {
					let rate = unescape($(this).attr('data-rate'));
					one_fm.purchase.move_item(item, null, warehouse, actual_qty, rate, function() { me.refresh(); });
				}
				else {
					one_fm.purchase.move_item(item, warehouse, null, actual_qty, null, function() { me.refresh(); });
				}
			}
		}

		function open_stock_entry(item, warehouse, entry_type) {
			frappe.model.with_doctype('Stock Entry', function() {
				var doc = frappe.model.get_new_doc('Stock Entry');
				if (entry_type) doc.stock_entry_type = entry_type;

				var row = frappe.model.add_child(doc, 'items');
				row.item_code = item;
				row.s_warehouse = warehouse;

				frappe.set_route('Form', doc.doctype, doc.name);
			})
		}

		// more
		this.content.find('.btn-more').on('click', function() {
			me.start += 21;
			me.refresh();
		});

	},
	refresh: function() {
		if(this.before_refresh) {
			this.before_refresh();
		}

		var me = this;
		frappe.call({
			method: 'one_fm.purchase.dashboard.item_dashboard_1.get_data',
			args: {
				rfm: this.rfm,
				start: this.start,
				sort_by: this.sort_by,
				sort_order: this.sort_order,
			},
			callback: function(r) {
				me.render(r.message);
			}
		});
	},
	render: function(data) {
		if(this.start===0) {
			this.max_count = 0;
			this.result.empty();
			$(frappe.render_template('item_dashboard_1_heading', {})).appendTo(this.result);
		}
		var context = this.get_item_dashboard_data(data, this.max_count, true);
		this.max_count = this.max_count;

		// show more button
		if(data && data.length===21) {
			this.content.find('.more').removeClass('hidden');

			// remove the last element
			data.splice(-1);
		} else {
			this.content.find('.more').addClass('hidden');
		}

		// If not any stock in any warehouses provide a message to end user
		if (context.data.length > 0) {
			$(frappe.render_template('item_dashboard_1_list', context)).appendTo(this.result);
		} else {
			var message = __(" Currently no stock available in any warehouse")
			$("<span class='text-muted small'>"+message+"</span>").appendTo(this.result);
		}
	},
	get_item_dashboard_data: function(data, max_count, show_item) {
		if(!max_count) max_count = 0;
		if(!data) data = [];

		data.forEach(function(d) {
			d.actual_or_pending = d.projected_qty + d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
			d.pending_qty = 0;
			d.total_reserved = d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
			if(d.actual_or_pending > d.actual_qty) {
				d.pending_qty = d.actual_or_pending - d.actual_qty;
			}

			max_count = Math.max(d.actual_or_pending, d.actual_qty,
				d.total_reserved, max_count);
		});

		var can_write = 0;
		if(frappe.boot.user.can_write.indexOf("Stock Entry")>=0){
			can_write = 1;
		}

		return {
			data: data,
			max_count: max_count,
			can_write:can_write,
			show_item: show_item || false
		}
	}
})

one_fm.purchase.move_item = function(item, source, target, actual_qty, rate, callback) {
	var dialog = new frappe.ui.Dialog({
		title: target ? __('Add Item') : __('Move Item'),
		fields: [
			{fieldname: 'item_code', label: __('Item'),
				fieldtype: 'Link', options: 'Item', read_only: 1},
			{fieldname: 'source', label: __('Source Warehouse'),
				fieldtype: 'Link', options: 'Warehouse', read_only: 1},
			{fieldname: 'target', label: __('Target Warehouse'),
				fieldtype: 'Link', options: 'Warehouse', reqd: 1},
			{fieldname: 'qty', label: __('Quantity'), reqd: 1,
				fieldtype: 'Float', description: __('Available {0}', [actual_qty]) },
			{fieldname: 'rate', label: __('Rate'), fieldtype: 'Currency', hidden: 1 },
		],
	})
	dialog.show();
	dialog.get_field('item_code').set_input(item);

	if(source) {
		dialog.get_field('source').set_input(source);
	} else {
		dialog.get_field('source').df.hidden = 1;
		dialog.get_field('source').refresh();
	}

	if(rate) {
		dialog.get_field('rate').set_value(rate);
		dialog.get_field('rate').df.hidden = 0;
		dialog.get_field('rate').refresh();
	}

	if(target) {
		dialog.get_field('target').df.read_only = 1;
		dialog.get_field('target').value = target;
		dialog.get_field('target').refresh();
	}

	dialog.set_primary_action(__('Submit'), function() {
		var values = dialog.get_values();
		if(!values) {
			return;
		}
		if(source && values.qty > actual_qty) {
			frappe.msgprint(__('Quantity must be less than or equal to {0}', [actual_qty]));
			return;
		}
		if(values.source === values.target) {
			frappe.msgprint(__('Source and target warehouse must be different'));
		}

		frappe.call({
			method: 'erpnext.stock.doctype.stock_entry.stock_entry_utils.make_stock_entry',
			args: values,
			freeze: true,
			callback: function(r) {
				frappe.show_alert(__('Stock Entry {0} created',
					['<a href="#Form/Stock Entry/'+r.message.name+'">' + r.message.name+ '</a>']));
				dialog.hide();
				callback(r);
			},
		});
	});

	$('<p style="margin-left: 10px;"><a class="link-open text-muted small">'
		+ __("Add more items or open full form") + '</a></p>')
		.appendTo(dialog.body)
		.find('.link-open')
		.on('click', function() {
			frappe.model.with_doctype('Stock Entry', function() {
				var doc = frappe.model.get_new_doc('Stock Entry');
				doc.from_warehouse = dialog.get_value('source');
				doc.to_warehouse = dialog.get_value('target');
				var row = frappe.model.add_child(doc, 'items');
				row.item_code = dialog.get_value('item_code');
				row.f_warehouse = dialog.get_value('target');
				row.t_warehouse = dialog.get_value('target');
				row.qty = dialog.get_value('qty');
				row.conversion_factor = 1;
				row.transfer_qty = dialog.get_value('qty');
				row.basic_rate = dialog.get_value('rate');
				frappe.set_route('Form', doc.doctype, doc.name);
			})
		});
}
