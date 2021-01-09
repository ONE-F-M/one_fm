from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Recruitment"),
			"items": [
				{
					"type": "doctype",
					"name": "ERF Request",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "ERF",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Interview Result",
				},
				{
					"type": "doctype",
					"name": "Career History",
				},
                {
					"type": "doctype",
					"name": "Best Reference",
				},
				{
					"type": "report",
					"name": "ERF Report",
					"is_query_report": True,
					"label": _("ERF Report"),
				}
			]
		},
		{
			"label": _("Recruitment Master"),
			"items": [
				{
					"type": "doctype",
					"name": "Recruitment Document Checklist",
				},
                {
					"type": "doctype",
					"name": "Recruitment Document Required",
                    "label": "Required Document"
				},
                {
					"type": "doctype",
					"name": "Visa Type",
				},
                {
					"type": "doctype",
					"name": "Recruitment Terms and Condition Template",
				},
                {
					"type": "doctype",
					"name": "OKR Performance Profile",
				},
				{
					"type": "doctype",
					"name": "Interview",
                    "label": "Interview Template",
				},
                {
					"type": "doctype",
					"name": "Country Calling Code",
				},
			]
		},
		{
			"label": _("Agency"),
			"items": [
				{
					"type": "doctype",
					"name": "Agency",
				},
                {
					"type": "doctype",
					"name": "Agency Contract",
				},
                {
					"type": "doctype",
					"name": "Demand Letter",
				}
			]
		}
	]
