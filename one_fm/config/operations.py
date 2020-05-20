from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
			"label": _("Operations Structure"),
			"items": [
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Project",
					"label": _("Operations Project")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Site",
					"label": _("Operations Site")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Shift",
					"label": _("Operations Shift")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Post Template",
					"label": _("Operations Post Template")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Post",
					"label": _("Operations Post")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Contracts",
					"label": _("Project Contract")
				},
			]
		},{
			"label": _("Operations Actions"),
			"items": [
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Task",
					"label": _("Operations Task")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "MOM",
					"label": _("MOM")
				},
			]
		}        
	]
