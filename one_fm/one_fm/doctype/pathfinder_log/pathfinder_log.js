// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pathfinder Log", {
	refresh(frm) {
		// Hide Status on new documents — it always defaults to Backlog
		// and cannot be meaningfully interacted with until the doc is saved.
		frm.toggle_display("status", !frm.is_new());

		// Restrict Epic link field to Work Items of type "Epic" only
		frm.set_query("epic", function () {
			return {
				filters: {
					work_item_type: "Epic",
				},
			};
		});

		set_deployed_read_only(frm);
	},

	status(frm) {
		set_deployed_read_only(frm);
	},
});

/**
 * Lock all user-editable fields when status is "Deployed",
 * leaving only the status field editable.
 * Restores full editability for any other status.
 *
 * Also controls the "Get Open Change Requests" button:
 * suppressed when Deployed to prevent server-side mutation
 * of change_requests while the form is locked.
 */
function set_deployed_read_only(frm) {
	const is_deployed = frm.doc.status === "Deployed";
	const editable_fields = [
		"process_name",
		"goal_description",
		"type",
		"process_owner_name",
		"change_requests",
	];

	editable_fields.forEach(function (fieldname) {
		frm.set_df_property(fieldname, "read_only", is_deployed ? 1 : 0);
	});

	// Remove any stale button instance before conditionally re-adding
	frm.remove_custom_button(__("Get Open Change Requests"));
	if (!frm.is_new() && !is_deployed) {
		frm.add_custom_button(
			__("Get Open Change Requests"),
			function () {
				frappe.call({
					method:
						"one_fm.one_fm.doctype.pathfinder_log.pathfinder_log.get_open_change_requests",
					args: {
						pathfinder_log: frm.doc.name,
					},
					freeze: true,
					freeze_message: __("Fetching open change requests…"),
					callback: function () {
						frm.reload_doc();
					},
				});
			}
		);
	}

	if (is_deployed) {
		frm.set_intro(
			__("This log is Deployed. Only the Status field can be changed."),
			"blue"
		);
	} else {
		frm.set_intro("");
	}
}
