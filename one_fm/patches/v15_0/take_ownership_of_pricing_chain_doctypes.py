import frappe

# WI-001707/708: the whole Pricing Proposal chain was built through the UI in production,
# so every one of these carries custom = 1. Frappe returns the base Document class for a
# custom doctype, which means the controllers never run - WI-001707's "only one enabled"
# and unique-effective-from checks, and WI-001713's Budget Configuration resolution, all
# silently do nothing. Clearing the flag is what binds the shipped JSON and its controller
# to the doctype.
PRICING_CHAIN_DOCTYPES = (
	"Budget Configuration",
	"Pricing Proposal",
	"Manpower Service Item",
	"Pricing Proposal Service Item",
	"Service Category",
	"Service Role",
)


def execute():
	"""
	Hand the Pricing Proposal chain over from UI-built custom doctypes to the app.

	Two symptoms this fixes:
	  * "Field service_category is referring to non-existing doctype Service Category" -
	    the two masters existed only in the production database.
	  * Controllers not running at all, because custom = 1 makes Frappe skip them.

	Registered under [pre_model_sync] so the flag is cleared before the model sync, letting
	the shipped JSON become the single source of truth. No-op for any doctype that does not
	exist yet - the sync creates it from the JSON.
	"""
	for doctype in PRICING_CHAIN_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		if frappe.db.get_value("DocType", doctype, "custom"):
			frappe.db.set_value(
				"DocType",
				doctype,
				{"custom": 0, "module": "One Fm"},
				update_modified=False,
			)

		frappe.clear_cache(doctype=doctype)
