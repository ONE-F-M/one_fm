from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Onboard Employee"),
			"items": [
				{
					"type": "doctype",
					"name": "Onboard Employee",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Candidate Orientation",
				},
				{
					"type": "doctype",
					"name": "Duty Commencement",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Work Contract",
				},
                {
					"type": "doctype",
					"name": "Candidate Orientation Checklist",
				}
			]
		},
		{
			"label": _("Recruitment"),
			"items": [
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
			"label": _("GETS"),
			"items": [
				{
					"type": "doctype",
					"name": "Job Opening Add",
				},
                {
					"type": "doctype",
					"name": "Head Hunt"
				},
                {
					"type": "doctype",
					"name": "Applicant Lead",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Applicant Lead Report",
					"doctype": "Applicant Lead"
				}
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
		},
		{
			"label": _("Training"),
			"items": [
				{
					"type": "doctype",
					"name": "Training Evaluation Form Template",
				},
                {
					"type": "doctype",
					"name": "Training Evaluation Form",
				},
                {
					"type": "doctype",
					"name": "Training Evaluation Form Response",
				}
			]
		},
		{
			"label": _("Indemnity"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Indemnity",
				},
                {
					"type": "doctype",
					"name": "Indemnity Allocation",
				},
                {
					"type": "doctype",
					"name": "Indemnity Policy",
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Indemnity Calculation",
					"doctype": "Employee"
				}
			]
		},
		{
			"label": _("Leaves"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Annual Leave Calculation",
					"doctype": "Employee"
				}
			]
		},
	]
