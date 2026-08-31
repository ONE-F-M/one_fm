import frappe

# WI-002102: the PAM License configuration the BA site holds, brought over so the licence
# compliance numbers can be built on it.
#
# Order matters. Occupational Sector is linked from PAM License Stats and PAM Designation
# List; PAM License Details owns the Stats child table; PAM Licenses links to
# PAM License Details; PAM File owns the PAM Licenses child table. A reload of a doctype
# whose Link target does not exist yet leaves a broken field.
NEW_DOCTYPES = (
	"occupational_sector",
	"pam_license_stats",
	"pam_license_details",
	"pam_licenses",
)

CHANGED_DOCTYPES = (
	"pam_file",
	"pam_designation_list",
)

# The BA site also carries Employee.custom_occupational_sector, fetched from the employee's
# PAM designation. Not brought over: tabEmployee is at MariaDB's row-size limit and the
# ALTER for another varchar(140) fails outright, so nothing can be added to it. The sector
# is read through one_fm_pam_designation -> PAM Designation List.occupational_sector where
# it is needed, which is where the value came from anyway and cannot go stale.


def execute():
	for doctype in NEW_DOCTYPES + CHANGED_DOCTYPES:
		frappe.reload_doc("grd", "doctype", doctype)

	verify()


def verify():
	"""The reloads are silent on a doctype whose Link target is missing, so the shape the
	calculations depend on is checked rather than assumed."""
	missing = [
		doctype
		for doctype in ("Occupational Sector", "PAM License Stats", "PAM License Details", "PAM Licenses")
		if not frappe.db.exists("DocType", doctype)
	]
	if missing:
		frappe.throw(f"WI-002102: {missing} were not created.")

	# The two links that hold the configuration together: a sector row points at a sector,
	# and a designation says which sector it is in. Either one missing and every compliance
	# number is counted against nothing.
	for doctype, fieldname, target in (
		("PAM License Stats", "occupational_sector", "Occupational Sector"),
		("PAM Designation List", "occupational_sector", "Occupational Sector"),
		("PAM License Details", "pam_license_stats", "PAM License Stats"),
		("PAM File", "pam_licenses", "PAM Licenses"),
		("PAM Licenses", "civil_id_number_for_licensing", "PAM License Details"),
	):
		field = frappe.get_meta(doctype).get_field(fieldname)
		if not field:
			frappe.throw(f"WI-002102: {doctype} has no {fieldname} field.")
		if field.options != target:
			frappe.throw(
				f"WI-002102: {doctype}.{fieldname} points at {field.options!r}, not {target!r}."
			)
