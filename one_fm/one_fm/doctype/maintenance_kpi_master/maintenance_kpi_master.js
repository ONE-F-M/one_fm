// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Maintenance KPI Master", {
	validate: function (frm) {
		// Rearrange the penalty tiers on screen before the save round-trips,
		// then flag any row whose logic the server will reject.
		sort_penalty_tiers(frm);
		highlight_bad_penalty_tiers(frm);
	},
});

function sort_penalty_tiers(frm) {
	const rows = frm.doc.penalty_information || [];
	if (!rows.length) {
		return;
	}

	// Highest Score Floor Threshold first, lowest last.
	rows.sort((a, b) => flt(b.score_floor_threshold) - flt(a.score_floor_threshold));
	rows.forEach((row, index) => {
		row.idx = index + 1;
	});

	frm.refresh_field("penalty_information");
}

function highlight_bad_penalty_tiers(frm) {
	const grid = frm.fields_dict.penalty_information.grid;
	const rows = frm.doc.penalty_information || [];

	let previous_floor = null;
	let previous_deduction = null;

	rows.forEach((row) => {
		const grid_row = grid.grid_rows_by_docname[row.name];
		let is_invalid = false;

		const current_floor = flt(row.score_floor_threshold);
		const current_deduction = flt(row.deduction_percentage);

		if (previous_floor !== null) {
			const duplicate_floor = current_floor === previous_floor;
			const cheaper_penalty = current_deduction <= previous_deduction;
			is_invalid = duplicate_floor || cheaper_penalty;
		}

		if (grid_row && grid_row.wrapper) {
			// bg-danger is a predefined Bootstrap utility class bundled with Frappe.
			grid_row.wrapper.toggleClass("bg-danger", is_invalid);
		}

		previous_floor = current_floor;
		previous_deduction = current_deduction;
	});
}
