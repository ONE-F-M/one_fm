frappe.listview_settings['PIFSS Form 103'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		var status_color = {
			"Submitted": "darkgrey",
			"Under Process": "blue",
			"Accepted": "green",
			"Rejected": "red",
		};
		return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
	},
	right_column: "grand_total"
};
