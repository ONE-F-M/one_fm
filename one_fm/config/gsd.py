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
				},
				{
					"type": "report",
					"name": "Accommodation Bed Detailed Report",
					"is_query_report": True,
					"label": _("Accommodation Bed Detailed Report"),
				},
				{
					"type": "report",
					"name": "Accommodation Checkin Checkout Report",
					"is_query_report": True,
					"label": _("Checkin Checkout Report"),
				},
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
		{
			"label": _("Purchasing"),
			"icon": "fa fa-star",
			"items": [
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
				{
					"type": "doctype",
					"name": "Purchase Order",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
					"description": _("Purchase Orders given to Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"]
				},
				{
					"type": "doctype",
					"name": "Purchase Settings",
					"onboard": 1,
					"label": _("One FM Purchase Settings")
				}
			]
		},
		{
			"label": _("Items"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"onboard": 1,
					"description": _("All Products or Services."),
				},
				{
					"type": "doctype",
					"name": "Item Group",
					"icon": "fa fa-sitemap",
					"label": _("Item Group"),
					"link": "Tree/Item Group",
					"description": _("Tree of Item Groups."),
				}
			]
		},
		{
			"label": _("Supplier"),
			"items": [
				{
					"type": "doctype",
					"name": "Supplier",
					"onboard": 1,
					"description": _("Supplier database."),
				},
				{
					"type": "doctype",
					"name": "Supplier Group",
					"description": _("Supplier Group master.")
				},
				{
					"type": "doctype",
					"name": "Contact",
					"description": _("All Contacts."),
				},
				{
					"type": "doctype",
					"name": "Address",
					"description": _("All Addresses."),
				},

			]
		},
		{
			"label": _("Stock Transactions"),
			"items": [
				{
					"type": "doctype",
					"name": "Stock Entry",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
				},
				{
					"type": "doctype",
					"name": "Warehouse",
					"onboard": 1,
				}
			]
		},
	]
