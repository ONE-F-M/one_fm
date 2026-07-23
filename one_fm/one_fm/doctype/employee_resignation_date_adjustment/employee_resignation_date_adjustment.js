// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Resignation Date Adjustment", {
	refresh: function(frm) {
		// is_corporate is computed server-side in set_approver() -- corporate
		// hires have no Operations Manager step, so their "Supervisor" is
		// really their Line Manager (matches Employee Resignation Withdrawal).
		frm.set_df_property('supervisor', 'label', frm.doc.is_corporate ? __('Line Manager') : __('Supervisor'));
		frm.refresh_field('supervisor');
	}
});
