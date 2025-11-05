frappe.listview_settings['Request for Material'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
        const status_colors = {
            "Draft": "grey",
            "Pending": "orange",
            "Approved": "blue",
            "Partially Ordered": "yellow",
            "Ordered": "green",
            "Partially Received": "yellow",
            "Received": "green",
            "Completed": "green",
            "Cancelled": "red",
            "Rejected": "red",
            "Accepted": "blue",
            "Issued": "green",
            "Transferred": "green",
            "Partially Issued": "yellow",
            "Partially Transferred": "yellow",
            "Stopped": "red",
            "Partial RFP": "yellow",
            "RFP Processed": "green"
        };
        return [__(doc.status), status_colors[doc.status] || "darkgrey", "status,=," + doc.status];
	}
};