// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Job Applicant Score"] = {
	"filters": [
		{
			"fieldname":"erf",
			"label": __("ERF"),
			"fieldtype": "Link",
			"options": "ERF"
		},
		{
			"fieldname":"agency",
			"label": __("Agency"),
			"fieldtype": "Link",
			"options": "Agency"
		}
	],
	"tree": true,
	"formatter": function(value, row, column, data, default_formatter) {
		if (column.fieldname=="job_applicant") {
			value = data.job_applicant || value;
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (!data.job_applicant) {
			value = $(`<span>${value}</span>`);

			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}

			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	"name_field": "job_applicant_score",
	"parent_field": "job_applicant",
	"initial_depth": 3
};
