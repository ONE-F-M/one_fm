frappe.listview_settings['Operations Role'] = {
	add_fields: ["paused"],
	get_indicator: function(doc) {
		if(!doc.paused) {
			return [__("Active"), "green", "paused,=,No"];
		} else if(doc.paused) {
			return [__("Paused"), "red", "paused,=,Yes"];
		}
	}
};