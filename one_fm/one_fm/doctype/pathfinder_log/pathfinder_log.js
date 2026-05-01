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
		setup_process_map_action(frm);
	},

	status(frm) {
		set_deployed_read_only(frm);
		setup_process_map_action(frm);
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

/**
 * Configure the "Process Map" option under the "Create" menu.
 * Visible only when status is "Active" and user has create permissions
 * for the target DocType. Opens in a new tab with prefilled process name.
 */
function setup_process_map_action(frm) {
	frm.page.remove_inner_button(__("Process Map"), __("Create"));

	if (frm.doc.status === "Active") {
		frm.page.add_inner_button(
			__("Process Map"),
			function () {
				const url = frappe.urllib.get_full_url(
					`/app/bpmn-process-model/new?process_name=${encodeURIComponent(frm.doc.process_name)}&pathfinder_log=${encodeURIComponent(frm.doc.name)}`
				);
				window.open(url, "_blank");
			},
			__("Create")
		);
	}
}
