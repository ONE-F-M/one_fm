// Copyright (c) 2020, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Checkpoints Route Assignment', {
	refresh: function(frm) {

	},

	loose_schedule: function(frm) {
		if(frm.doc.loose_schedule == 1) {
			cur_frm.clear_table("checkpoints_route_table");
			cur_frm.refresh_fields();

		}
		if(frm.doc.loose_schedule == 0) {
			cur_frm.clear_table("checkpoints_route_assignment_loose_schedule_table");
			cur_frm.refresh_fields();

		}


	},

	validate: function(frm) {
		if(frm.doc.start_repeat_time > frm.doc.end_repeat_time) {
			frappe.msgprint(__("Start Repeat Time needs to be Less than the End Repeat Time"));
            frappe.validated = false;
		}
	},

	// }
});
