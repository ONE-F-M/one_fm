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
		}
	]
