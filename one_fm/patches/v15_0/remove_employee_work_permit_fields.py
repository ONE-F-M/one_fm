"""WI-002618: retire the two work-permit fields on Employee and re-point what read them.

Three separate things, all of which have to happen together or the form is left in a state
nobody asked for.

1. ``one_fm_work_permit`` and ``pam_type`` go. delete_custom_fields removes the Custom
   Field rows without touching the Employee columns, so the stored values are still there
   if the business changes its mind - nothing here destroys data.

2. ``residency_expiry_date`` has a depends_on that names pam_type:

       eval:doc.under_company_residency==1 && doc.pam_type != "Kuwaiti"

   set by patches/v15_0/update_residency_expiry_date_depends_on. Left alone, that half of
   the condition reads a field that no longer exists - undefined != "Kuwaiti" is true - so
   the field would quietly start showing for the 149 employees it was written to hide it
   from. Dropping that half is the only reading that stays coherent once the field it asks
   about is gone, and it is called out on the PR because it IS a visible change.

3. The visa date is relabelled. create_custom_fields updates a field that already exists,
   so re-running the Employee set is what applies the new label.

Ordered so the label update runs before the deletions - create_custom_fields walks the
whole set, and the two removed fields are no longer in it.
"""

import frappe

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.setup.setup import delete_custom_fields

RESIDENCY_EXPIRY = "Employee-residency_expiry_date"
RESIDENCY_EXPIRY_DEPENDS_ON = "eval:doc.under_company_residency==1"

REMOVED = {
	"Employee": [
		{"fieldname": "one_fm_work_permit"},
		{"fieldname": "pam_type"},
	]
}


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	# Applies the new "Date of Visa Expiry" label, and re-links the two fields whose
	# insert_after pointed at what is about to be removed.
	create_custom_fields(get_employee_custom_fields())

	delete_custom_fields(REMOVED)

	if frappe.db.exists("Custom Field", RESIDENCY_EXPIRY):
		frappe.db.set_value(
			"Custom Field", RESIDENCY_EXPIRY, "depends_on", RESIDENCY_EXPIRY_DEPENDS_ON
		)

	frappe.clear_cache(doctype="Employee")
