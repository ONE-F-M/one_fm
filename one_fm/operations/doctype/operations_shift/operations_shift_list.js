frappe.listview_settings['Operations Shift'] = {
	get_indicator: function(doc) {
		if(doc.status == "Active") {
			return [__("Active"), "green", ];
		} else if(doc.status == "Not Active") {
			return [__("Not Active"), "red", ];
		}
	}
};