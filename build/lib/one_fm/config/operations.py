from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
			"label": _("Operations Structure"),
			"items": [
				{
					"type": "doctype",
					"name": "Project",
					"onboard": 1,
					"label": _("Project")
				},
                {
					"type": "doctype",
					"onboard": 1,
					"name": "Operations Site",
					"label": _("Site")
				},
                {
					"type": "doctype",
					"onboard": 1,
					"name": "Operations Shift",
					"label": _("Shift")
				},
                {
					"type": "doctype",
					"name": "Post Type",
					"onboard": 1,
					"label": _("Post Type")
				},
                {
					"type": "doctype",
					"onboard": 1,
					"name": "Operations Post",
					"label": _("Post")
				},
                {
					"onboard": 1,
					"type": "doctype",
					"name": "Contracts",
					"label": _("Project Contract")
				},
			]
		},{
			"label": _("Operations Actions"),
			"items": [
				{
					"onboard": 1,
					"type": "doctype",
					"name": "Post Allocation Plan",
					"label": _("Post Allocation")
				},
				{
					"onboard": 1,
					"type": "doctype",
					"name": "Task",
					"label": _("Task")
				},
                {
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
					"onboard": 1,
					"type": "doctype",
					"name": "Employee Schedule",
					"label": _("Employee Schedule")
				},
				{
					"onboard": 1,
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
					"onboard": 1,
					"type": "doctype",
					"name": "Shift Report",
					"label": _("Shift Report")
				},
				{
					"onboard": 1,
					"type": "doctype",
					"name": "Post Handover",
					"label": _("Post Handover")
				},
			]
		}     
	]
