from frappe import _


def get_data(**kwargs):
	return {
		"heatmap": True,
		"heatmap_message": _("This is based on the Time Sheets created against this project"),
		"fieldname": "project",
		"transactions": [
			{
				"label": _("Project"),
				"items": ["Task", "Timesheet", "Issue", "Project Update"],
			},
			{"label": _("Material"), "items": ["Material Request", "BOM", "Stock Entry"]},
			# WI-001776: Contracts sits beside Sales Order so a Project Manager can see,
			# open and raise a project's contracts from the one place. Contracts carries a
			# standard `project` link field, so the badge count, the pre-filtered list and
			# the prefilled new-Contract form all come from the dashboard's own fieldname.
			{"label": _("Sales"), "items": ["Sales Order", "Contracts", "Delivery Note", "Sales Invoice"]},
			{"label": _("Purchase"), "items": ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
			{"label": _("Operations"), "items": ["MOM", "Operations Site", "Operations Shift", "Operations Role", "Operations Post"]},
		],
	}
