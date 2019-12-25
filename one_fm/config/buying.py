from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Purchasing"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Item Request",
					"onboard": 1,
					"dependencies": ["Employee"],
					"description": _("Item Request given to Employee."),
				},
				{
					"type": "doctype",
					"name": "Stock Check",
					"onboard": 1,
					"dependencies": ["Item","Item Group"],
					"description": _("Stock Check."),
				},
			]
		},
	]
