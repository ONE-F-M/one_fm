frappe.listview_settings['ERF'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status=="Draft") {
			return [__("Draft"), "orange"];
		} else if(doc.status=="Accepted") {
			return [__("Accepted"), "blue"];
		} else if(doc.status=="Closed") {
			return [__("Closed"), "green"];
		} else if(doc.status=="Declined") {
			return [__("Declined"), "red"];
		}
	}
};
