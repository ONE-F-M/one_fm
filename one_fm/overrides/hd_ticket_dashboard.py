from frappe import _

def get_data(**kwargs):
    return {
		"heatmap": True,
		"heatmap_message": _("This is based on the Error Log created against this Ticket"),
		"fieldname": "hd_ticket",
		"transactions": [
			{"label": _("Related"), "items": ["Error Log"]},
		],
	}