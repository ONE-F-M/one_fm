"""WI-002883: keep PACI Number on the Accommodation list once Status joins it.

Frappe caps how many columns a list view draws, by window width:

    let total_fields = 6;
    if (window.innerWidth <= 1366) total_fields = 4;
    else if (window.innerWidth >= 1920) total_fields = 10;
    this.columns = this.columns.slice(0, this.list_view_settings.total_fields || total_fields);

The columns are the title, a tag column, and then every `in_list_view` field in order.
Accommodation had four of those besides its title - accommodation, type, ownership,
accommodation_paci_number - which came to exactly six. Adding Status made five, and at any
window between 1367 and 1919 pixels the sixth slot went to Status and PACI Number fell off
the end. Measured on this bench: at 1604px the header reads

    Code | Accommodation Name | Type | Status | Ownership | ID

and at 1920px PACI Number is back.

Nothing is wrong with either field - the budget is simply spent. A List View Settings row
raises it so both fit at every width.

The row is created here rather than shipped as a fixture because List View Settings is a
per-site preference: it also carries whichever columns an operator has chosen for
themselves, and a fixture would overwrite those on every migrate. Only the cap is written,
and an existing row keeps everything else it holds.
"""

import frappe

DOCTYPE = "List View Settings"
LIST_VIEW = "Accommodation"

# Enough for the title, the tag column, the five in_list_view fields and the name column.
# The field is a Select; "8" is one of its options.
TOTAL_FIELDS = "8"


def execute():
	if frappe.db.exists(DOCTYPE, LIST_VIEW):
		# Only the cap. The rest of the row is whoever configured the list's.
		frappe.db.set_value(DOCTYPE, LIST_VIEW, "total_fields", TOTAL_FIELDS)
	else:
		frappe.get_doc(
			{"doctype": DOCTYPE, "name": LIST_VIEW, "total_fields": TOTAL_FIELDS}
		).insert(ignore_permissions=True)

	verify()


def verify():
	saved = frappe.db.get_value(DOCTYPE, LIST_VIEW, "total_fields")
	if saved != TOTAL_FIELDS:
		frappe.throw(
			f"WI-002883: the {LIST_VIEW} list view still caps at {saved!r}, so PACI Number "
			"drops off below 1920px."
		)

	shown = [
		field.fieldname
		for field in frappe.get_meta(LIST_VIEW).fields
		if field.in_list_view
	]
	# The title is drawn as the subject column rather than as one of these, and the tag
	# column takes a slot of its own - so the cap has to clear the rest by two.
	if len(shown) + 2 > int(TOTAL_FIELDS):
		frappe.throw(
			f"WI-002883: {LIST_VIEW} now shows {len(shown)} fields in its list view, which "
			f"needs a cap above {TOTAL_FIELDS}."
		)
