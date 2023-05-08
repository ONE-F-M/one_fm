frappe.listview_settings['Operations Role'] = {
	add_fields: ["is_active"],
	get_indicator: function(doc) {
		if(doc.status == "Active") {
			return [__("Active"), "green", ];
		} else if(doc.status == "InActive") {
			return [__("InActive"), "red", ];
		}
	}
};
