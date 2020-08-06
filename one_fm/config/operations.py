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
					"name": "Project",
					"label": _("Project")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Site",
					"label": _("Site")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Shift",
					"label": _("Shift")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Post Type",
					"label": _("Post Type")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Operations Post",
					"label": _("Post")
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
					"name": "Task",
					"label": _("Task")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "MOM",
					"label": _("MOM")
				},
			]
		},
		{
			"label": _("Roster"),
			"items": [
				{
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Roster",
					"label": _("Roster")
				},
			]
		}        
	]
