import frappe

# Service Location becomes a Link to Location on both appointment doctypes
# (WI-001807), and this is its default on each.
DEFAULT_SERVICE_LOCATION = "Personnel Identification Dept - Um Alhayman"

APPOINTMENT_DOCTYPES = ("Fingerprint Appointment", "Medical Appointment")


def execute():
	"""Give every Service Location already in use a Location to point at (WI-001807).

	Service Location was free text, so the values on existing appointments - and the
	default the field ships with - are not Location records. Runs before the model
	sync so the field is never a Link with nothing valid to select.

	The new Locations carry no coordinates: they are real places whose position only
	GRD and Transportation can supply, and a wrong pin is worse than an empty one.
	"""
	in_use = set()
	for doctype in APPOINTMENT_DOCTYPES:
		in_use.update(
			frappe.get_all(doctype, pluck="service_location", distinct=True) or []
		)

	wanted = {(name or "").strip() for name in in_use} | {DEFAULT_SERVICE_LOCATION}

	for location_name in sorted(filter(None, wanted)):
		if frappe.db.exists("Location", location_name):
			continue

		frappe.get_doc(
			{
				"doctype": "Location",
				"location_name": location_name,
				"is_group": 0,
				# Mandatory custom field; 0 is what the existing stop locations use.
				"geofence_radius": 0,
			}
		).insert(ignore_permissions=True)

	# A value stored with stray whitespace would dangle once the field is a Link.
	for doctype in APPOINTMENT_DOCTYPES:
		for name, value in frappe.get_all(
			doctype, fields=["name", "service_location"], as_list=True
		):
			if value and value != value.strip():
				frappe.db.set_value(
					doctype, name, "service_location", value.strip(), update_modified=False
				)
