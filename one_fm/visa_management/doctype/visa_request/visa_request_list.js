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

			export_visa_request_zip(names);
		});
	}
};

// fetch rather than open_url_post: a form POST replaces the page with the raw error when
// the server refuses, and this keeps the user on the list with a normal message.
async function export_visa_request_zip(names) {
	frappe.dom.freeze(__("Preparing ZIP file..."));
	try {
		const response = await fetch(
			"/api/method/one_fm.visa_management.doctype.visa_request.visa_request.export_zip",
			{
				method: "POST",
				headers: {"X-Frappe-CSRF-Token": frappe.csrf_token},
				body: new URLSearchParams({names: JSON.stringify(names)}),
			}
		);
		if (!response.ok) {
			frappe.msgprint({
				title: __("Export ZIP File"),
				indicator: "red",
				message: await server_error_message(response),
			});
			return;
		}
		const link = document.createElement("a");
		link.href = URL.createObjectURL(await response.blob());
		link.download = "Visa Requests.zip";
		link.click();
		URL.revokeObjectURL(link.href);
	} finally {
		frappe.dom.unfreeze();
	}
}

async function server_error_message(response) {
	try {
		const data = await response.json();
		if (data._server_messages) {
			return JSON.parse(data._server_messages).map(m => JSON.parse(m).message).join("<br>");
		}
	} catch (e) {
		// Not a JSON error body; fall through to the generic message.
	}
	return __("The ZIP file could not be created.");
}
