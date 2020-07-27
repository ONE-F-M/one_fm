# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "One Fm",
			"color": "grey",
			"icon": "octicon octicon-file-directory",
			"type": "module",
			"label": _("One Fm")
		},
		{
		"module_name": "GRD",
			"category": "Modules",
			"label": _("GRD"),
			"color": "#2ecc71",
			"icon": "octicon octicon-organization",
			"type": "module"
		},
		{
			"module_name": "Operations",
			"label": _("Operations"),
			"color": "grey",
			"icon": "fa fa-cogs",
			"type": "module"
		},
		{
			"module_name": "Purchase",
			"label": _("Purchase"),
			"color": "grey",
			"icon": "fa fa-cogs",
			"type": "module"
		},
		{
			"module_name": "Legal",
			"label": _("Legal"),
			"color": "grey",
			"icon": "fa fa-gavel",
			"type": "module"
		}
	]
