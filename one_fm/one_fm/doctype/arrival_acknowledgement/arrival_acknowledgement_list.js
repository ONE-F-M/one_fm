// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

function arrival_acknowledgement_get_selected_same_day(listview) {
	let items = listview.get_checked_items();
	if (!items.length) {
		frappe.msgprint(__("Select at least one record."));
		return null;
	}

	let dates = [...new Set(items.map((d) => d.arrival_date))];
	if (dates.length > 1) {
		frappe.msgprint(__("All selected records must have the same Arrival Date. Selected dates: {0}", [dates.join(", ")]));
		return null;
	}

	return items;
}

frappe.listview_settings["Arrival Acknowledgement"] = {
	onload: function(listview) {
		listview.page.add_action_item(__("Bulk Acknowledge"), function() {
			let items = arrival_acknowledgement_get_selected_same_day(listview);
			if (!items) {
				return;
			}

			// Orientation/Site fields (General Services, Operations) must already be
			// filled in and saved on each record individually -- bulk_acknowledge()
			// reports back per-record if any selected record is still missing them.
			listview.call_for_selected_items(
				"one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement.bulk_acknowledge"
			);
		});

		listview.page.add_action_item(__("Bulk Confirm Arrival"), function() {
			let items = arrival_acknowledgement_get_selected_same_day(listview);
			if (!items) {
				return;
			}

			if (items.some((d) => d.department !== "Transportation")) {
				frappe.msgprint(__("Bulk Confirm Arrival only applies to Transportation records."));
				return;
			}

			frappe.prompt([
				{ label: __("Outcome"), fieldname: "outcome", fieldtype: "Select", options: ["Arrived", "Did Not Arrive"], reqd: 1 },
			], function(values) {
				listview.call_for_selected_items(
					"one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement.bulk_confirm_arrival",
					values
				);
			}, __("Bulk Confirm Arrival (Transportation)"), __("Submit"));
		});
	}
};
