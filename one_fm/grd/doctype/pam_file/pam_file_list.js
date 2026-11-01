frappe.listview_settings["PAM File"] = {
	add_fields: ["file_status"],
	get_indicator(doc) {
		if (doc.file_status === "Active") {
			return [__("Active"), "green", "file_status,=,Active"];
		}
		if (doc.file_status === "Inactive") {
			return [__("Inactive"), "red", "file_status,=,Inactive"];
		}
	},
};
