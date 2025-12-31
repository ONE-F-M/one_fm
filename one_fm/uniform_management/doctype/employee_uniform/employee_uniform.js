// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Uniform', {
	refresh: function(frm) {
		if(frm.doc.type == "Return"){
			frappe.meta.get_docfield("Employee Uniform Item", 'returned', frm.doc.name).hidden = true;
			// frappe.meta.get_docfield("Employee Uniform Item", 'quantity', frm.doc.name).label = 'Return Qty';
		}
		frm.set_query("warehouse", function() {
			return {
				filters: {'is_uniform_warehouse': true}
			}
		});
		if(frm.is_new() && frm.doc.stock_entry){
			frm.set_value("stock_entry", "");
		}
		add_quality_feedback_schedule(frm)
	},
	employee: function(frm) {
		set_uniform_details(frm);
		set_filters(frm);
	},
	type: function(frm) {
		set_uniform_details(frm);
		if(frm.doc.type == "Return"){
			frappe.meta.get_docfield("Employee Uniform Item", 'returned', frm.doc.name).hidden = true;
			// frappe.meta.get_docfield("Employee Uniform Item", 'quantity', frm.doc.name).label = 'Return Qty';
		}
	},
	has_employee_left: function(frm) {
		update_employees_list(frm)
	},
	get_item_data: function(frm, item) {
		if (!item.item || frm.doc.type=='Return') return;
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item,
					doctype: frm.doc.doctype,
					buying_price_list: frappe.defaults.get_default('buying_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					name: frm.doc.name,
					qty: item.quantity || 1,
					company: frm.doc.company,
					conversion_rate: 1,
					plc_conversion_rate: 1
				}
			},
			callback: function(r) {
				const d = item;
				if(!r.exc) {
					d['rate'] = r.message.price_list_rate;
					frm.refresh_field('uniforms')
				}
			}
		});
	},
});

frappe.ui.form.on('Employee Uniform Item', {
	uniforms_add: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(frm.doc.issued_on && frm.doc.type == "Issue") {
			row.expire_on = frappe.datetime.add_months(frm.doc.issued_on, 12);
			refresh_field("expire_on", cdn, "uniforms");
		}
	},
	item: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
	},
	quantity: function(frm, doctype, name) {
		const item = locals[doctype][name];
		if(frm.doc.type == 'Return'){
			if(item.actual_quantity && item.quantity && item.quantity > item.actual_quantity){
				item.quantity = item.actual_quantity
				refresh_field("quantity", name, "uniforms");
				frappe.throw(__("Could not exceed the Quantity than {0}",[item.actual_quantity]));
			}
		}
	}
});

var set_filters = function(frm) {
	if(frm.doc.type == "Return"){
		frm.set_query("item", "uniforms", function() {
			return {
				query: "one_fm.uniform_management.doctype.employee_uniform.employee_uniform.issued_items_not_returned",
				filters: {'employee': frm.doc.employee}
			}
		});
	}
};

var set_uniform_details = function(frm) {
	frm.clear_table('uniforms');
	if(frm.doc.employee && frm.doc.type){
		frappe.call({
			doc: frm.doc,
			method: 'set_uniform_details',
			callback: function(r) {
				if(!r.exc){
					frm.refresh_fields()
				}
			},
			freeze: true,
			freeze_message: __('Fetching Uniform Details..')
		});
	}
};

var update_employees_list = function(frm) {
	frm.set_query('employee', () => {
		return {
			filters: {
				status: frm.doc.has_employee_left ? 'Left' : 'Active',
			}
		};
	});
};

var get_quality_feedback_templates = function (callback) {
	frappe.call({
		method:
			"one_fm.uniform_management.doctype.employee_uniform.employee_uniform.get_quality_feedback_templates",
		callback: function (r) {
			if (!r.exc) {
				callback(r.message);
			}
		},
	});
};

var add_quality_feedback_schedule = function (frm) {
	if (
		frm.doc.docstatus == 1 &&
		frm.doc.type === "Issue" &&
		frm.doc.uniforms.length > 0
	) {
		frm.add_custom_button(
			__("Quality Feedback"),
			function () {
				get_quality_feedback_templates(function (templates) {
					let fields = [
						{
							fieldname: "quality_feedback_table",
							fieldtype: "Table",
							cannot_add_rows: true,
							in_place_edit: true,
							data: frm.doc.uniforms.map((row) => {
								return {
									item_code: row.item,
									item_name: row.item_name,
									item_type: row.item_type,
									quantity: row.quantity,
								};
							}),
							fields: [
								{
									fieldname: "item_code",
									label: __("Item Code"),
									fieldtype: "Link",
									options: "Item",
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldname: "item_name",
									label: __("Item Name"),
									fieldtype: "Data",
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldname: "item_type",
									label: __("Item Type"),
									fieldtype: "Link",
									options: "Item Type",
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldname: "quantity",
									label: __("Quantity"),
									fieldtype: "Int",
									read_only: 1,
									in_list_view: 1,
								},
								{
									fieldname: "quality_feedback_template",
									label: __("Quality Feedback Template"),
									fieldtype: "Link",
									options: "Quality Feedback Template",
									in_list_view: 1,
									get_query(doc) {
										return {
											filters: {
												custom_is_enabled: 1,
												custom_item_type: doc.item_type,
											},
										};
									},
								},
								{
									fieldname: "version_no",
									label: __("Version No."),
									fieldtype: "Data",
									read_only: 1,
									in_list_view: 1,
								},
							],
						},
					];

					let d = new frappe.ui.Dialog({
						title: __("Quality Feedback"),
						fields: fields,
						primary_action_label: __("Generate"),
						primary_action(values) {
							let selected_rows =
								(values && values.quality_feedback_table) || [];

							let selected_templates = selected_rows
								.filter((row) => row.quality_feedback_template)
								.map((row) => {
									return {
										item_code: row.item_code,
										quality_feedback_template: row.quality_feedback_template,
									};
								});

							if (!selected_templates.length) {
								frappe.msgprint(
									__("Please select at least one Quality Feedback Template.")
								);
								return;
							}

							frappe.call({
								method:
									"one_fm.uniform_management.doctype.employee_uniform.employee_uniform.create_item_specific_quality_feedbacks",
								args: {
									employee_uniform: frm.doc.name,
									selected_feedback_templates: selected_templates,
								},
								callback: function (r) {
									if (!r.exc) {
										frappe.msgprint(__("Quality Feedback Scheduled Successfully"));
										d.hide();
									}
								},
							});
						},
					});

					d.fields_dict.quality_feedback_table.grid.fields_map.quality_feedback_template.onchange =
						function (e) {
							let selected_template = this.get_value();
							if (selected_template) {
								let selected_row = this.grid_row.doc;
								let template = templates.find(
									(t) => t.name === selected_template
								);
								if (template) {
									selected_row.version_no = template.custom_version;
									this.grid_row.refresh();
								}
							}
						};

					d.show();
				});
			},
			__("Create")
		);
	}
};

