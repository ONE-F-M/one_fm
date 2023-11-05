frappe.provide('one_fm.purchase');

one_fm.purchase.PendingPurchaseBoard = Class.extend({
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
		
		
		this.content = $(frappe.render_template('pending_purchase_docs_')).appendTo(this.parent);
		
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
			method: 'one_fm.purchase.page.pending_purchase_doc.pending_purchase_docs.get_data',
			callback: function(r) {
				me.render(r.message);
			}
		});
	},
	render: function(data) {
		if(this.start===0) {
			this.max_count = 0;
			this.result.empty();
			$(frappe.render_template('pending_purchase_docs_heading', {})).appendTo(this.result);
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
			$(frappe.render_template('pending_purchase_docs_list', context)).appendTo(this.result);
		} else {
			var message = __("No Pending Purchase Documents Found")
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

