// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Routine Task', {
	refresh: function(frm) {
		frm.set_query("erp_document", function() {
			return {
				query: "one_fm.operations.doctype.routine_task.routine_task.filter_routine_document",
				filters: {'parent': frm.doc.process_name}
			}
		});
	}
});
