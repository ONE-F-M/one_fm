frappe.listview_settings['Leave Application'] = {
	add_fields: ["leave_type", "employee", "employee_name", "total_leave_days", "from_date", "to_date"],
	get_indicator: function (doc) {
		if (doc.status === "Approved") {
			return [__("Approved"), "green", "status,=,Approved"];
		} else if (doc.status === "Rejected") {
			return [__("Rejected"), "red", "status,=,Rejected"];
		} else if (doc.docstatus === 2 || doc.status==="Cancelled") {
			return [__("Cancelled"), "red", "status,=,Cancelled"];

		} else if(doc.status==="Open"){
			return [__("Open"), "lightblue", "status,=,Open"];
		}
	}
};
