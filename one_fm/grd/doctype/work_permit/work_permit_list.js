frappe.listview_settings['Work Permit'] = {
	add_fields: ["work_permit_status", "date_of_application", "civil_id", "employee_name"],
	// filters: [["status","=", "Active"]],
	// get_indicator: function(doc) {
	// 	var indicator = [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
	// 	indicator[1] = {"Active": "green", "Temporary Leave": "red", "Left": "darkgrey"}[doc.status];
	// 	return indicator;
	// }
};