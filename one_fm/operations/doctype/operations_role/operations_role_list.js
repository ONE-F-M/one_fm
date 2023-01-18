frappe.listview_settings['Operations Role'] = {
	add_fields: ["is_active"],
	get_indicator: function(doc) {
		if(doc.is_active == 1) {
			return [__("Active"), "green", "status,=,Active"]
		} else if(doc.is_active != 1) {
			return [__("Inactive"), "grey", "status,=,Inactive"]
		}
	}
};
