from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
			"label": _("Operations Structure"),
			"items": [
				{
					# "color": "grey",
					"type": "doctype",
					"name": "Project",
					"onboard": 1,
					"label": _("Project")
				},
                {
					# "color": "grey",
					"type": "doctype",
					"onboard": 1,
					"name": "Operations Site",
					"label": _("Site")
				},
                {
					# "color": "grey",
					"type": "doctype",
					"onboard": 1,
					"name": "Operations Shift",
					"label": _("Shift")
				},
                {
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Post Type",
					"onboard": 1,
					"label": _("Post Type")
				},
                {
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"type": "doctype",
					"onboard": 1,
					"name": "Operations Post",
					"label": _("Post")
				},
                {
					# "color": "grey",
					"onboard": 1,
					# "icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Contracts",
					"label": _("Project Contract")
				},
			]
		},{
			"label": _("Operations Actions"),
			"items": [
				{
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"onboard": 1,
					"type": "doctype",
					"name": "Task",
					"label": _("Task")
				},
                {
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"onboard": 1,
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
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"onboard": 1,
					"type": "doctype",
					"name": "Employee Schedule",
					"label": _("Roster")
				},
				{
					# "color": "grey",
					"onboard": 1,
					# "icon": "octicon octicon-key",
					"type": "doctype",
					"name": "Post Schedule",
					"label": _("Post Schedule")
				},
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"onboard": 1,
					"type": "doctype",
					"name": "Shift Report",
					"label": _("Shift Report")
				},
				{
					# "color": "grey",
					# "icon": "octicon octicon-key",
					"onboard": 1,
					"type": "doctype",
					"name": "Post Handover",
					"label": _("Post Handover")
				},
			]
		}     
	]
