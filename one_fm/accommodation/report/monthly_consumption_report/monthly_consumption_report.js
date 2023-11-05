// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Monthly Consumption Report"] = {
	"filters": get_filters()
};

function get_filters() {
	filters = [
		{
			"fieldname":"reading_type",
			"label": __("Reading Type"),
			"fieldtype": "Select",
			"options": "Common\nUnit",
			"default": "Common"
		},
		{
			"fieldname":"accommodation",
			"label": __("Accommodation"),
			"fieldtype": "Link",
			"options": "Accommodation"
		},
		{
			"fieldname":"accommodation_unit",
			"label": __("Accommodation Unit"),
			"fieldtype": "Link",
			"options": "Accommodation Unit"
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year")
		},
		{
			"fieldname":"meter_type",
			"label": __("Meter Type"),
			"fieldtype": "Select",
			"options": "Electricity\nWater",
			"default": "Electricity"
		}
	]
	return filters;
};
