"""WI-002823: the Employee fields hidden by Under Company Residency are always shown.

Seven fields disappeared from the Employee form whenever the Under Company Residency box
was unticked - the PAM file and its number, the PAM designation, the work permit and its
salary and expiry, and the residency expiry. Tick the box and they came back.

That is what made the data invisible rather than absent. An employee who is not on the
company's residency can still hold a PAM designation, still have a work permit expiring,
and still be the one somebody is looking for when they open the form - and every one of
those values is on the record whether the form draws the field or not. Hiding them meant
the only way to see them was to tick a box that changes what the record says.

The values themselves are untouched. This clears the condition; nothing is written to any
Employee.

`update_residency_expiry_date_depends_on` and `remove_employee_work_permit_fields` both
set the residency expiry's condition when they ran. They are historical and are left as
they are - this patch runs after them, and a fresh install applies the fixture (which now
carries an empty condition) before either.
"""

import frappe

from one_fm.custom.custom_field.employee import get_employee_custom_fields

DOCTYPE = "Employee"

# The gate itself is not in the list. Under Company Residency has never had a condition of
# its own; these are the fields that hung off it.
GATED_FIELDS = (
	"pam_file",
	"pam_file_number",
	"one_fm_pam_designation",
	"work_permit",
	"work_permit_salary",
	"work_permit_expiry_date",
	"residency_expiry_date",
)


def execute():
	for fieldname in GATED_FIELDS:
		name = f"{DOCTYPE}-{fieldname}"
		if not frappe.db.exists("Custom Field", name):
			continue

		# Written directly rather than through create_custom_fields: that helper only
		# applies the keys it is handed, and a site whose row already holds the condition
		# would keep it if the fixture had simply dropped the key. The fixture carries an
		# empty string for the same reason.
		frappe.db.set_value("Custom Field", name, "depends_on", "", update_modified=False)

	frappe.clear_cache(doctype=DOCTYPE)
	verify()


def verify():
	standing = frappe.get_all(
		"Custom Field",
		filters={"dt": DOCTYPE, "depends_on": ["like", "%under_company_residency%"]},
		pluck="fieldname",
	)
	if standing:
		frappe.throw(
			f"WI-002823: {standing} still disappear when Under Company Residency is "
			"unticked."
		)

	# The fixture has to agree, or the next migrate that runs the Employee custom field
	# set puts every condition straight back.
	gated_in_fixture = [
		field["fieldname"]
		for fields in get_employee_custom_fields().values()
		for field in fields
		if "under_company_residency" in (field.get("depends_on") or "")
	]
	if gated_in_fixture:
		frappe.throw(
			f"WI-002823: {gated_in_fixture} still carry the condition in the fixture, so "
			"the next migrate would put it back."
		)
