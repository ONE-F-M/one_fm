// The Temporary Deployment Workflow is inactive (Processa sets workflow_state), so Frappe
// no longer renders the state itself. Colours mirror the Workflow State styles.
const TD_STATE_COLOURS = {
	"Draft": "red",
	"Pending Approval": "orange",
	"Approved": "green",
	"Rejected": "gray",
	"Cancelled": "red",
};

frappe.listview_settings["Temporary Deployment"] = {
	add_fields: ["workflow_state"],
	has_indicator_for_draft: 1,
	has_indicator_for_cancelled: 1,

	get_indicator(doc) {
		if (doc.workflow_state) {
			return [
				__(doc.workflow_state),
				TD_STATE_COLOURS[doc.workflow_state] || "gray",
				"workflow_state,=," + doc.workflow_state,
			];
		}
	},
};
