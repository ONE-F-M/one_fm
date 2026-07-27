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

var add_quality_feedback_schedule = function (frm) {
	   if (frm.doc.docstatus == 1 && frm.doc.type === "Issue" && frm.doc.uniforms.length > 0) {
		   frm.add_custom_button(__("Quality Feedback"), function () {
			   const fields = [
				   {
					   fieldname: "quality_feedback_table",
					   fieldtype: "Table",
					   label: __("Uniform Details"),
					   cannot_add_rows: true,
					   in_place_edit: true,
					   reqd: 1,
					   fields: [
						   { fieldname: "item_code", label: __("Item Code"), fieldtype: "Link", options: "Item", read_only: 1, in_list_view: 1, columns: 1 },
						   { fieldname: "item_name", label: __("Item Name"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 2 },
						   { fieldname: "item_type", label: __("Item Type"), fieldtype: "Link", options: "Item Type", read_only: 1, in_list_view: 1, columns: 2 },
						   { fieldname: "quantity", label: __("Qty"), fieldtype: "Float", read_only: 1, in_list_view: 1, columns: 1 },
						   { fieldname: "quality_feedback_template", label: __("Template"), fieldtype: "Link", options: "Quality Feedback Template", in_list_view: 1, columns: 2, get_query(doc) { return { filters: { custom_is_enabled: 1, custom_item_type: doc.item_type } }; } },
						   { fieldname: "feedback_template_version", label: __("Ver."), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 1 },
					   ],
				   },
			   ];

			   let d = new frappe.ui.Dialog({
				   title: __("Quality Feedback"),
				   fields: fields,
				   size: "large",
				   cssClass: "quality-feedback-dialog-wide",
				   primary_action_label: __("Generate"),
				   primary_action(values) {
					   let all_rows = (values && values.quality_feedback_table) || [];
					   let selected_feedbacks = all_rows.filter(row => row.quality_feedback_template);
					   if (!selected_feedbacks.length) {
						   frappe.msgprint(__("Please select at least one Quality Feedback Template."));
						   return;
					   }
					   frappe.call({
						   method: "one_fm.uniform_management.doctype.employee_uniform.employee_uniform.create_quality_feedbacks",
						   args: {
							   employee_uniform: frm.doc.name,
							   selected_feedbacks: selected_feedbacks // each object has item and template info
						   },
						   callback: function (r) {
							   if (!r.exc) {
								   frappe.msgprint(__("Quality Feedback Scheduled Successfully"));
								   d.hide();
							   }
						   },
					   });
				   }
			   });

			   // Pre-populate table rows with data from uniforms table
			   let grid = d.fields_dict.quality_feedback_table.grid;
			   let uniforms = frm.doc.uniforms || [];
			   let item_codes_to_fetch = uniforms.filter(u => !u.item_type || u.item_type === "").map(u => u.item);

			   function fill_rows(itemTypeMap) {
				   // Build the rows up front and assign them directly to the grid's
				   // data array. add_new_row() only works once the grid has been
				   // rendered (after d.show()), so populating it before showing the
				   // dialog leaves get_data() empty.
				   grid.df.data = uniforms.map((uniform, idx) => ({
					   idx: idx + 1,
					   __islocal: true,
					   item_code: uniform.item,
					   item_name: uniform.item_name,
					   item_type: uniform.item_type || itemTypeMap[uniform.item] || "",
					   quantity: uniform.quantity,
					   // Template and version left for user selection
				   }));
				   d.show();
				   grid.refresh();
				   // Attach event for template selection to auto-fill version synchronously
				   setTimeout(function() {
					   let $dialog = $(d.$wrapper);
					   if (grid) {
						   $dialog.on('change blur', 'input[data-fieldname="quality_feedback_template"]', function(e) {
							   let $input = $(this);
							   let value = $input.val();
							   let $row = $input.closest('.grid-row');
							   let row_idx = $row.index();
							   let data = grid.get_data();
							   let row = data[row_idx];
							   if (value && row) {
								   frappe.call({
									   method: "frappe.client.get",
									   args: { doctype: "Quality Feedback Template", name: value },
									   callback: function (r) {
										   if (r.message && (r.message.custom_version_no || r.message.version_no)) {
											   row.feedback_template_version = r.message.custom_version_no || r.message.version_no;
											   grid.refresh();
										   }
									   },
								   });
							   } else if (row) {
								   row.feedback_template_version = "";
								   grid.refresh();
							   }
						   });
					   }
				   }, 200);
			   }

			   if (item_codes_to_fetch.length > 0) {
				   frappe.call({
					   method: "one_fm.uniform_management.doctype.employee_uniform.employee_uniform.get_item_types",
					   args: { items: item_codes_to_fetch },
					   callback: function(r) {
						   let item_type_map = {};
						   if (r.message && Array.isArray(r.message)) {
							   item_codes_to_fetch.forEach((code, idx) => { item_type_map[code] = r.message[idx]; });
						   }
						   fill_rows(item_type_map);
					   }
				   });
			   } else {
				   fill_rows({});
			   }
		   },
		   __("Create")
		   );
	   }
}

