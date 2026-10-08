// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

const VISA_REQUEST_EXPORT_ZIP_LIMIT = 50;

frappe.listview_settings["Visa Request"] = {
	onload: function(listview) {
		listview.page.add_actions_menu_item(__("Export ZIP File"), function() {
			const names = listview.get_checked_items().map(row => row.name);

			if (names.length === 0) {
				frappe.msgprint(__("Please select at least one Visa Request."));
				return;
			}
			if (names.length > VISA_REQUEST_EXPORT_ZIP_LIMIT) {
				frappe.msgprint(
					__("You can export at most {0} Visa Requests at a time. You selected {1}.",
						[VISA_REQUEST_EXPORT_ZIP_LIMIT, names.length])
				);
				return;
			}

			open_url_post(
				"/api/method/one_fm.visa_management.doctype.visa_request.visa_request.export_zip",
				{names: JSON.stringify(names)}
			);
		});
	}
};
