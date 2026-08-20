import frappe

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	EXEMPT_SECTOR,
	SECTOR_EXPAT_ALLOWANCE,
)

# WI-002099: the occupational sectors PAM rations a licence by, as the BA site holds them.
# Master data rather than a fixture list in code: a licence's sector rows link to these
# records, and the expatriate allowance table is keyed on their names.
SECTORS = tuple(SECTOR_EXPAT_ALLOWANCE) + (EXEMPT_SECTOR,)


def execute():
	frappe.reload_doc("grd", "doctype", "occupational_sector")

	for sector in SECTORS:
		if not frappe.db.exists("Occupational Sector", sector):
			frappe.get_doc({
				"doctype": "Occupational Sector",
				"occupational_sector_type": sector,
			}).insert(ignore_permissions=True)

	verify()


def verify():
	missing = [sector for sector in SECTORS if not frappe.db.exists("Occupational Sector", sector)]
	if missing:
		frappe.throw(
			f"WI-002099: {missing} were not created. The expatriate allowance is keyed on these "
			"names, so a sector row linked to anything else gets no allowance."
		)
