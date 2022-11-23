// frappe.listview_settings['Operations Post'] = {
// 	add_fields: ["paused"],
// 	get_indicator: function(doc) {
// 		if(!doc.paused) {
// 			return [__("Active"), "green", "paused,=,No"];
// 		} else if(doc.paused) {
// 			return [__("Paused"), "red", "paused,=,Yes"];
// 		}
// 	}
// };


frappe.listview_settings['Operations Post'] = {
	add_fields: ["paused"],
	get_indicator: function(doc) {
		if(doc.status == "Active") {
			return [__("Active"), "green", ];
		} else if(doc.status == "Inactive") {
			return [__("Inactive"), "red", ];
		}
	}
};