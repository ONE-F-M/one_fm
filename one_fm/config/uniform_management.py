from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Uniform Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Uniform",
					"label": _("Uniform Issue/Return"),
					"onboard": 1
				}
			]
		},
		{
			"label": _("Master"),
			"items": [
				{
					"type": "doctype",
					"name": "Designation Profile",
					"label": _("Designation Profile"),
					"onboard": 1
				}
			]
		}
	]
