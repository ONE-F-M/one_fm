// The Penalty Workflow is inactive (Processa sets workflow_state), so Frappe
// no longer renders the state itself. Colours mirror the Workflow State styles.
const PENALTY_STATE_COLOURS = {
	"Penalty Issued": "blue",
	"Penalty Accepted": "green",
	"Penalty Rejected": "red",
};

frappe.listview_settings["Penalty"] = {
	add_fields: ["workflow_state"],

	get_indicator(doc) {
		if (doc.workflow_state) {
			return [
				__(doc.workflow_state),
				PENALTY_STATE_COLOURS[doc.workflow_state] || "gray",
				"workflow_state,=," + doc.workflow_state,
			];
		}
	},
};
