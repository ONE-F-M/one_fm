// Copyright (c) 2020, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on('Penalty', {
	refresh: function(frm){
		if(!frm.doc.__islocal){
			$('.actions-btn-group').hide();

			frm.fields_dict["penalty_details"].grid.set_column_disp("period_start_date", 0);
			frm.fields_dict["penalty_details"].grid.set_column_disp("period_lapse_date", 0);

			frm.fields_dict["penalty_details"].grid.toggle_enable("penalty_levied", 0);
			frm.fields_dict["penalty_details"].grid.toggle_enable("penalty_type", 0);
			frm.fields_dict["penalty_details"].grid.toggle_enable("exact_notes", 0);
			frm.fields_dict["penalty_details"].grid.toggle_enable("attachments", 0);
		}
	}
});
