from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("One FM Purchasing"),
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
					"name": "Request for Supplier Quotation",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Purchase Request",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Supplier Purchase Order",
					"onboard": 1,
				},
			]
		}
        
	]
