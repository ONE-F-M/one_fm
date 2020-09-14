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
					"label": _("Accommodation List"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Accommodation Unit",
					"label": _("Units List"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Accommodation Space",
					"label": _("Space List"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Bed",
					"label": _("Beds List"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Book Bed",
					"label": _("Book Bed"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Accommodation Checkin",
					"label": _("Accommodation Checkin")
				}
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
