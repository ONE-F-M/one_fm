// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance Service Level Agreement", {
	refresh: function (frm) {
		// Populate status options when document_type is set
		if (frm.doc.document_type) {
			set_status_options(frm);
		}
	},

	document_type: function (frm) {
		// When Apply On DocType changes, fetch its status field options
		// and populate SLA Fulfilled On / Paused On child tables
		if (frm.doc.document_type) {
			set_status_options(frm);
		}
	},
});

function set_status_options(frm) {
	// Fetch the status field options from the target DocType
	frappe.model.with_doctype(frm.doc.document_type, function () {
		var meta = frappe.get_meta(frm.doc.document_type);
		var status_field = null;

		for (var i = 0; i < meta.fields.length; i++) {
			if (meta.fields[i].fieldname === "status") {
				status_field = meta.fields[i];
				break;
			}
		}

		if (status_field && status_field.options) {
			var options = status_field.options
				.split("\n")
				.filter(function (opt) {
					return opt.trim() !== "";
				});

			// Set options for SLA Fulfilled On Status child table
			frm.fields_dict.sla_fulfilled_on.grid.update_docfield_property(
				"status",
				"options",
				options.join("\n")
			);

			// Set options for Pause SLA On Status child table
			frm.fields_dict.pause_sla_on.grid.update_docfield_property(
				"status",
				"options",
				options.join("\n")
			);
		}
	});
}
