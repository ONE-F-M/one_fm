// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bug Buster Report', {
	refresh: function(frm) {
		if (frm.is_new()){
			frm.trigger('set_values');
		}
	},
	set_values: function(frm) {
		if (frm.is_new()){
			frm.set_value('date', frappe.datetime.nowdate());
			frm.set_value('time', frappe.datetime.now_time());
			frm.set_value('bug_buster', '');
			frm.set_value('bug_buster_name', '');
		}
	}
});
