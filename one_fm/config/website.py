from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Web Site"),
			"items": [
				{
					"type": "doctype",
					"name": "Website Info",
					"description": _("Website Info"),
				}
			]
		}
	]
