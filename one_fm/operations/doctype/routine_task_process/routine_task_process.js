// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Routine Task Process', {
	refresh: function(frm) {
		frm.set_query("routine_task_document", "erp_document", function() {
			return {
				query: "one_fm.operations.doctype.routine_task_process.routine_task_process.filter_routine_document"
			}
		});
	}
});
