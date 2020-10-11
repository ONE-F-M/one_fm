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
					"name": "Accommodation Checkin Checkout",
					"label": _("Checkin/Checkout")
				}
			]
		},
		{
			"label": _("Accommodation Master"),
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
		},
		{
			"label": _("Data"),
			"icon": "fa fa-th",
			"items": [
				{
					"type": "doctype",
					"name": "Data Export",
					"label": _("Export Data"),
					"icon": "octicon octicon-cloud-upload",
					"description": _("Export Data in CSV / Excel format.")
				}
			]
		},
		{
			"label": _("Accommodation Reports"),
			"icon": "fa fa-th",
			"items": [
				{
					"type": "report",
					"name": "Unit Bed Space Report",
					"is_query_report": True,
					"label": _("Unit Bed Space Report"),
				},
				{
					"type": "report",
					"name": "Accommodation Bed Space Report",
					"is_query_report": True,
					"label": _("Accommodation Bed Space Report"),
				}
			]
		},
		{
			"label": _("Uniform Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Uniform",
					"label": _("Uniform Issue/Return"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Designation Uniform Profile",
					"label": _("Designation Uniform Profile"),
					"onboard": 1
				}
			]
		},
	]
