from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
			"label": _("Assets"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer Asset",
					"onboard": 1,
				},
			]
		}
    ]