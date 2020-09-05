from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Accommodation"),
			"items": [
				{
					"type": "doctype",
					"name": "Accommodation",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Accommodation Unit",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Accommodation Space",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Bed",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Master"),
			"items": [
				{
					"type": "doctype",
					"name": "Accommodation Type"
				},
				{
					"type": "doctype",
					"name": "Accommodation Space Type"
				},
				{
					"type": "doctype",
					"name": "Bed Space Type"
				},
				{
					"type": "doctype",
					"name": "Governorate"
				},
				{
					"type": "doctype",
					"name": "Governorate Area"
				}
			]
		}
	]
