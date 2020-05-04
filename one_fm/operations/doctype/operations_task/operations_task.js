// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operations Task', {
	onload: function(frm) {
		frm.set_query("task", "depends_on", function() {
			var filters = {
				name: ["!=", frm.doc.name]
			};
			if(frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters
			};
		})
	},

	refresh: function(frm) {
		frm.fields_dict['parent_task'].get_query = function () {
			return {
				filters: {
					"is_group": 1,
				}
			}
		}

		if (!frm.doc.is_group) {
			if (!frm.is_new()) {
				if (frappe.model.can_read("Timesheet")) {
					frm.add_custom_button(__("Timesheet"), () => {
						frappe.route_options = { "project": frm.doc.project, "task": frm.doc.name }
						frappe.set_route("List", "Timesheet");
					}, __("View"), true);
				}

				if (frappe.model.can_read("Expense Claim")) {
					frm.add_custom_button(__("Expense Claims"), () => {
						frappe.route_options = { "project": frm.doc.project, "task": frm.doc.name };
						frappe.set_route("List", "Expense Claim");
					}, __("View"), true);
				}
			}
		}
	},

	setup: function(frm) {
		frm.fields_dict.project.get_query = function() {
			return {
				query: "one_fm.operations.doctype.operations_task.operations_task.get_project"
			}
		};
	},

	is_group: function (frm) {
		frappe.call({
			method: "one_fm.operations.doctype.operations_task.operations_task.check_if_child_exists",
			args: {
				name: frm.doc.name
			},
			callback: function (r) {
				if (r.message.length > 0) {
					frappe.msgprint(__(`Cannot convert it to non-group. The following child Tasks exist: ${r.message.join(", ")}.`));
					frm.reload_doc();
				}
			}
		})
	},

	validate: function(frm) {
		frm.doc.project && frappe.model.remove_from_locals("Operations Project",
			frm.doc.project);
	},

});
