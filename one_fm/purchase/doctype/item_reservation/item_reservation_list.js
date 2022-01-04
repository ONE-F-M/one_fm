frappe.listview_settings['Item Reservation'] = {
	// add_fields: ["name", "status", "item_code", "qty",
    //     "issued_qty", "from_date", "to_date"],
	get_indicator: function(doc) {
		const status_colors = {
			"Draft": "yellow",
			"Active": "green",
			"Completed": "grey",
			"Cancelled": "red"
		};
		return [__(doc.status), status_colors[doc.status], "status,=,"+doc.status];
	}//,
	// right_column: "grand_total"
};
