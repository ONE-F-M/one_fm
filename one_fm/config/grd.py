from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Ministry of Justice"),
			"items": [
				{
					"type": "doctype",
					"name": "Article Of Association",
					"onboard": 1,
				},{
					"type": "doctype",
					"name": "Changes of Article of Association",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Public Authority for Manpower"),
			"items": [
				{
					"type": "doctype",
					"name": "PAM Salary Certificate",
					"onboard": 1,
				},{
					"type": "doctype",
					"name": "PAM File",
					"onboard": 1,
				},{
					"type": "doctype",
					"name": "PAM Authorized Signatory List",
					"onboard": 1,
				},
			]
		},
		 {
			"label": _("Public Institution for Social Security"),
			"items": [
				{
					"type": "doctype",
					"name": "Public Institution for Social Security",
					"onboard": 1,
				},
			]
		},
		 {
			"label": _("Ministry of Commerce and Industry"),
			"items": [
				{
					"type": "doctype",
					"name": "MOCI License",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Public Authority for Civil Information"),
			"items": [
				{
					"type": "doctype",
					"name": "PACI Number",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("GRD Settings"),
			"items": [
				{
					"type": "doctype",
					"name": "PAM Designation List",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "PAM Salary Certificate Setting",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "PAM Authorized Signatory Setting",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("PIFSS"),
			"items": [
				{
					"type": "doctype",
					"name": "PIFSS Form 103",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "PIFSS Form 55",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "PIFSS Monthly Deduction",
					"onboard": 1,
				},
			]
		}
	]
