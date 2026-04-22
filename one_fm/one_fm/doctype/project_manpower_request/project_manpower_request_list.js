// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.listview_settings['Project Manpower Request'] = {
	hide_name_column: true,
	add_fields: ["workflow_state"],
	get_indicator: function (doc) {
		const workflow_state = doc.workflow_state || "";
		const workflow_state_colors = {
			"Draft": "gray",
			"Pending OM Approval": "orange",
			"Awaiting Recruiter Approval": "blue",
			"Approved": "green",
			"Completed": "green",
			"Cancelled": "red",
			"Rejected": "red",
			"Internal Fulfilled": "light-green",
			"Fulfilled by OT": "blue",
			"Fulfilled by Sub-con": "purple",
			"Fulfilled by OT & Sub": "darkgray",
			"Withdrawal Resignation": "yellow"
		};

		const indicator_color = workflow_state_colors[workflow_state]
			|| (/reject|cancel/i.test(workflow_state) ? "red"
				: /approve|complete|fulfill/i.test(workflow_state) ? "green"
					: /pending|awaiting|approval/i.test(workflow_state) ? "orange"
						: /draft/i.test(workflow_state) ? "gray"
							: "gray");

		return [__(workflow_state), indicator_color, "workflow_state,=," + workflow_state];
	}
};
