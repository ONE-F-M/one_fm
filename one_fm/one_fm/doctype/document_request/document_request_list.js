// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings["Document Request"] = {
	add_fields: ["workflow_state"],
	get_indicator(doc) {
		const state = doc.workflow_state;
		if (!state) {
			return;
		}
		let colour = "orange";
		if (state === "Approved") {
			colour = "green";
		} else if (/Rejected|Withdrawn/.test(state)) {
			colour = "red";
		}
		return [__(state), colour, `workflow_state,=,${state}`];
	},
};
