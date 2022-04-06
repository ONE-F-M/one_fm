// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Accommodation Checkin Checkout Report"] = {
	"filters": [
		{
			"fieldname":"accommodation",
			"label": __("Accommodation"),
			"fieldtype": "Link",
			"options": "Accommodation"
		},
		{
			"fieldname":"accommodation_unit",
			"label": __("Unit"),
			"fieldtype": "Link",
			"options": "Accommodation Unit"
		},
		{
			"fieldname":"accommodation_space",
			"label": __("Space"),
			"fieldtype": "Link",
			"options": "Accommodation Space",
			"get_query": function(){
				return {
					"filters": {
						'bed_space_available': 1
					}
				}
			}
		},
		{
			"fieldname":"bed",
			"label": __("Bed"),
			"fieldtype": "Link",
			"options": "Bed"
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname":"employee_id",
			"label": __("Employee ID"),
			"fieldtype": "Data"
		},
		{
			"fieldname":"tenant_category",
			"label": __("Tenant Category"),
			"fieldtype": "Select",
			"options": "\nGranted Service\nPaid Service"
		},
		{
			"fieldname":"current_list_only",
			"label": __("Current List Only"),
			"fieldtype": "Check",
			"default": true
		},
	]
};
