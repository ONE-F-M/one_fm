"""WI-002775: the Quota Type records the business analyst's site already holds.

The DocType arrives with the app; its records do not. Three of them exist on the BA site
and every downstream story counts against them by name - the Quota Classification table
groups by Quota Type, and a PAM Designation links to one - so a site with the table and
none of the types has a quota structure nobody can fill in.

Seeded rather than left to be typed, because the names are what the counting joins on.
An existing record is left exactly as it is: the business owns this master, and a site
that has renamed or added to it is not one this patch should argue with.
"""

import frappe

DOCTYPE = "Quota Type"

# As the BA site holds them. These are the three PAM rations a licence's visas in.
QUOTA_TYPES = ("Basic", "Heavy Driver", "Light Driver")


def execute():
	for quota_type in QUOTA_TYPES:
		if frappe.db.exists(DOCTYPE, quota_type):
			continue

		frappe.get_doc({"doctype": DOCTYPE, "quota_type": quota_type}).insert(
			ignore_permissions=True
		)

	verify()


def verify():
	missing = [name for name in QUOTA_TYPES if not frappe.db.exists(DOCTYPE, name)]
	if missing:
		frappe.throw(f"WI-002775: the Quota Types {missing} were not created.")

	if not frappe.get_meta("PAM Designation List").get_field("quota_type"):
		frappe.throw(
			"WI-002775: PAM Designation List has no quota_type field, so no designation "
			"can be put in a quota and every classification count would be zero."
		)
