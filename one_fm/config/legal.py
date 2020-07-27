from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
			"label": _("Legal"),
			"items": [
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Penalty Type",
					"label": _("Penalty Type")
				},
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Penalty List",
					"label": _("Penalty List")
				},
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Penalty Issuance",
					"label": _("Penalty Issuance")
				},
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Penalty",
					"label": _("Penalty")
				},
			]
		},
		{
			"label": _("Legal Investigation"),
			"items": [
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Legal Investigation",
					"label": _("Legal Investigation")
				},
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Legal Investigation Session",
					"label": _("Legal Investigation Session")
				},
			]
		}        
	]
