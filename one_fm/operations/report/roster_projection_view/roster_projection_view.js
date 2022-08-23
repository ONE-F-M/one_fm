// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Roster Projection View"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"reqd": 1 ,
			"options": [
				{ "value": 01, "label": __("Jan") },
				{ "value": 02, "label": __("Feb") },
				{ "value": 03, "label": __("Mar") },
				{ "value": 04, "label": __("Apr") },
				{ "value": 05, "label": __("May") },
				{ "value": 06, "label": __("June") },
				{ "value": 07, "label": __("July") },
				{ "value": 08, "label": __("Aug") },
				{ "value": 09, "label": __("Sep") },
				{ "value": 10, "label": __("Oct") },
				{ "value": 11, "label": __("Nov") },
				{ "value": 12, "label": __("Dec") },
			],
			"default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1
		},
		{
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Select",
            "options": [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033],
            "reqd": 1,
            "default": Number(frappe.datetime.get_today().split('-')[0])
        }

	],
	"formatter": function (value, row, column, data, default_formatter) {
        if(window.location.href.includes('prepared_report_name')){
            let message = $('.form-message.text-muted.small');
            message[0].style.display = 'block';
            message[0].innerHTML = `<span style="color:blue;">
                <b>NOTE:</b><br />
                1) Projection Data is based on Roster Data only and is a snapshot from the first of the month. Any Roster Changes that Occurred After the First Day of the Month does not reflect in the Projection Column.<br>
                2) Live Projection Data is Real Live Data of the Roster and Actual attendance. As well the attendance data is based on the Day before yesterday's Attendance and Yesterdays's Roster.
            </span>
            `;
        }

        return value
	}
};



