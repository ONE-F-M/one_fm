// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance KPI Assessment", {
	refresh(frm) {
		// AC2: The penalty summary is entirely system-generated. Forcefully lock
		// the Monthly Penalty Details grid so the "Add Row" and "Delete Row"
		// buttons are hidden and no manual typing is possible in its columns.
		frm.set_df_property("monthly_penalty_assessment", "read_only", 1);

		const grid = frm.fields_dict.monthly_penalty_assessment.grid;
		grid.cannot_add_rows = true;
		grid.cannot_delete_rows = true;
		grid.refresh();
	},
});
