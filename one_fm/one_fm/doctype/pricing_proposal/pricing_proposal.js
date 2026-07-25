// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pricing Proposal", {
	date_of_inception(frm) {
		// Re-fetch the applicable Budget Configuration whenever the date changes; the
		// same resolution runs server-side on save, this only makes it immediate.
		if (!frm.doc.date_of_inception) {
			frm.set_value("budget_configuration", null);
			return;
		}

		frappe.call({
			method: "one_fm.one_fm.doctype.pricing_proposal.pricing_proposal.get_applicable_budget_configuration",
			args: { date_of_inception: frm.doc.date_of_inception },
			callback: (r) => {
				frm.set_value("budget_configuration", r.message || null);

				if (!r.message) {
					frappe.msgprint({
						title: __("Budget Configuration Not Found"),
						message: __("No Budget Configuration is effective on or before {0}. Create one before pricing this proposal.", [
							frappe.format(frm.doc.date_of_inception, { fieldtype: "Date" }),
						]),
						indicator: "orange",
					});
				}
			},
		});
	},
});
