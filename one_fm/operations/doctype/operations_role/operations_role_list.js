frappe.listview_settings['Operations Role'] = {
	get_indicator: function(doc) {
		if(!doc.status) {
			return [__("Active"), "green", "status,=,Active"];
		} else if(doc.status == 'Active') {
			return [__("Active"), "green", "status,=,Active"]
		} else if(doc.status == 'Hold') {
			return [__("Hold"), "orange", "status,=,Hold"]
		} else if(doc.status == 'Stop') {
			return [__("Stop"), "red", "status,=,Stop"]
		} else if(doc.status == 'Cancelled') {
			return [__("Cancelled"), "grey", "status,=,Cancelled"]
		}
	}
};
