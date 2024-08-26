// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Validator"] = {
	"filters": [
		{
            "fieldname": "to_date",
            "label": __("Date"),
            "fieldtype": "Date",
			'default':new Date(new Date().getFullYear(), new Date().getMonth(), 1),
            "reqd": 1,
        },
		{
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
			"options": "Warehouse",
            "reqd": 1,
        },
		{
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Link",
			"options": "Item",
            
        },
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
        {
			"fieldname": "show_only_issues",
            "label": __("Show Only Items with Issues"),
			"fieldtype": "Check",
			'default':0
        },
	]
};
