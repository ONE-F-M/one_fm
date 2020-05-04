from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
			"label": _("Operations"),
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
					"name": "Site",
					"label": _("Site")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Site Shift",
					"label": _("Site Shift")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Post Type Template",
					"label": _("Post Type Template")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Site Post",
					"label": _("Site Post")
				},
                {
					"color": "grey",
					"icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Contracts",
					"label": _("Project Contract")
				},
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
