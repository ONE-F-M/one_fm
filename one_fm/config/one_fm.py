from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Purchasing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item Group",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Item",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Supplier",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Request for Material",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Request for Purchase",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quotation Comparison Sheet",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quotation From Supplier",
					"onboard": 1,
				},
			]
		}

	]
