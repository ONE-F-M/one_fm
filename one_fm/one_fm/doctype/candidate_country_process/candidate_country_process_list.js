// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

const CCP_SYNC_METHOD =
	"one_fm.one_fm.doctype.candidate_country_process.candidate_country_process.bulk_sync_with_template";

frappe.listview_settings["Candidate Country Process"] = {
	onload(listview) {
		if (!frappe.model.can_write("Candidate Country Process")) {
			return;
		}
		listview.page.add_inner_button(__("Sync Template"), () => open_sync_template_dialog(listview));
		listview.page.add_action_item(__("Sync Template"), () => open_sync_template_dialog(listview));
	},
};

function open_sync_template_dialog(listview) {
	const selected = listview.get_checked_items(true);
	const scopes = {
		[__("Only the selected trackers ({0})", [selected.length])]: "selected",
		[__("All In Process trackers")]: "in_process",
		[__("All trackers")]: "all",
	};
	const dialog = new frappe.ui.Dialog({
		title: __("Sync Template"),
		fields: [
			{
				fieldname: "scope",
				fieldtype: "Select",
				label: __("Trackers to sync"),
				options: Object.keys(scopes),
				default: Object.keys(scopes)[selected.length ? 0 : 1],
				reqd: 1,
			},
			{
				fieldtype: "HTML",
				options: `<p class="text-muted small">${__(
					"Each tracker takes the latest steps, durations and dependencies from its Agency Country Process. Dates, linked records and step statuses are kept."
				)}</p>`,
			},
		],
		primary_action_label: __("Sync"),
		primary_action(values) {
			const scope = scopes[values.scope];
			if (scope === "selected" && !selected.length) {
				frappe.throw(__("Select at least one tracker in the list."));
			}
			dialog.hide();
			frappe.call({
				method: CCP_SYNC_METHOD,
				args: { scope, names: scope === "selected" ? selected : null },
				freeze: true,
				freeze_message: __("Syncing trackers..."),
				callback: () => listview.refresh(),
			});
		},
	});
	dialog.show();
}
