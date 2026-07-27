import frappe


def execute():
	"""
	Hand Vehicle Handover Log over from a UI-built custom doctype to the app (WI-001576).

	It was created through Customize/New DocType in production with ``custom = 1``, so it
	lived only in the database and no repo JSON governed it. This patch clears the custom
	flag (and pins the module) *before* the model sync, so the doctype JSON now shipped in
	the app becomes the single source of truth and the two new fields - Status and Total
	Kilometers - are created by the normal sync.

	Registered under [pre_model_sync] for that ordering. No-op on a site where the doctype
	does not exist yet: the sync simply creates it from the JSON.
	"""
	if not frappe.db.exists("DocType", "Vehicle Handover Log"):
		return

	frappe.db.set_value(
		"DocType",
		"Vehicle Handover Log",
		{"custom": 0, "module": "One Fm"},
		update_modified=False,
	)

	frappe.clear_cache(doctype="Vehicle Handover Log")
