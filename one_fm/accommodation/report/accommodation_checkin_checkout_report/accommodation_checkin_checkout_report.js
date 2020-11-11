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
			"fieldname":"accommodation_not_provided_by_company",
			"label": __("Not Provided by Company"),
			"fieldtype": "Check"
		}
	]
};
