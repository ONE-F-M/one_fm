import frappe

# WI-001708: the two masters Manpower Service Item links to.
SERVICE_MASTERS = ("Service Category", "Service Role")


def execute():
	"""
	Hand Service Category and Service Role over from UI-built custom doctypes to the app.

	Both were created through New DocType in production with ``custom = 1``, so they lived
	only in that database - which is why Pricing Proposal failed to open anywhere else with
	"Field service_category is referring to non-existing doctype Service Category". The
	doctype JSONs are now shipped in the app; this clears the custom flag (and pins the
	module) *before* the model sync so the shipped JSON becomes the single source of truth.

	Registered under [pre_model_sync] for that ordering. No-op on a site where they do not
	exist yet - the sync simply creates them from the JSON.
	"""
	for doctype in SERVICE_MASTERS:
		if not frappe.db.exists("DocType", doctype):
			continue

		frappe.db.set_value(
			"DocType",
			doctype,
			{"custom": 0, "module": "One Fm"},
			update_modified=False,
		)
		frappe.clear_cache(doctype=doctype)
