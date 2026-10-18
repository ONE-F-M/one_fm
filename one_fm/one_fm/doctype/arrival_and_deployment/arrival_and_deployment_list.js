// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

const ARRIVAL_BULK_METHOD = "one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment";

frappe.listview_settings["Arrival and Deployment"] = {
	onload(listview) {
		listview.page.add_action_item(__("Submit to Onboarding (one email)"), () => {
			listview.call_for_selected_items(`${ARRIVAL_BULK_METHOD}.bulk_submit_to_onboarding`);
		});

		listview.page.add_action_item(__("Confirm Onboarding (one email)"), () => {
			listview.call_for_selected_items(`${ARRIVAL_BULK_METHOD}.bulk_confirm_onboarding`);
		});

		listview.page.add_action_item(__("Attach Ticket"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) {
				frappe.throw(__("Select at least one arrival."));
			}
			frappe.prompt(
				[{ fieldname: "ticket", fieldtype: "Attach", label: __("Ticket"), reqd: 1 }],
				(values) => {
					listview.call_for_selected_items(`${ARRIVAL_BULK_METHOD}.bulk_attach_ticket`, {
						file_url: values.ticket,
					});
				},
				__("Attach one ticket to {0} arrivals", [names.length]),
				__("Attach")
			);
		});
	},
};
